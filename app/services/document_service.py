import json
import asyncio
import pandas as pd
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import os
import traceback

from sqlalchemy import select, func, desc, text, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import make_transient

from core.error_handle import MyException
import core.database as db
from core.extends_logger import logger
from core.i18n import _
from core import config
from schemas.document import DocumentList

from models.models import Document, OcrResult, FileType, ProcessingStatus, OcrEngine
from parser import OcrParser
from parser import OCRResult as OcrParserResult # Rename to avoid conflict with model
from parser import OcrAnalyzer
from fastapi import WebSocket

from services.websocket_manager import progress_manager

import torch

class DocumentService:
    def __init__(self):
        pass

    def save_document(self, document_data: Document, user_id: str) -> Document:
        """
        Save a document (create or update).
        
        Args:
            document_data: Document data dictionary
            user_id: ID of the user
            
        Returns:
            Document: The saved document
        """
        print("save_document 000000 ")
        if document_data.id:
            return self.update_document(document_data, user_id)
        return self.create_document(document_data, user_id)

    def create_document(self, document_data: Document, user_id: str) -> Document:
        """
        Create a new OCR document record.
        
        Args:
            document_data: Document data with required fields
            user_id: ID of the user creating the document
            
        Returns:
            Document: The created document
        """
        with db.get_sync_session() as session:  
            try:
                document = Document()
                document.filename = document_data.filename
                if document_data.file_type and document_data.file_type.lower() in ["png", "jpg", "jpeg"]:
                    document.file_type = FileType.image
                elif document_data.file_type and document_data.file_type.lower() in ["pdf"]:
                    document.file_type = FileType.pdf
                document.file_path = document_data.file_path
                document.file_size = document_data.file_size
                document.status = ProcessingStatus.pending
                document.created_by = user_id
                document.updated_by = user_id
                
                session.add(document)
                session.commit()
                session.refresh(document)
                make_transient(document)
                
                return document
            except (ValueError, TypeError) as e:
                session.rollback()
                logger.error(f"Invalid document data: {e}")
                traceback.print_exc()
                raise MyException(code=400, msg=_("Invalid document data format"))
            except IntegrityError as e:
                session.rollback()
                logger.error(f"Failed to create document: {e}")
                raise MyException(code=400, msg=_("Failed to create document. Please check the data and try again."))

    def update_document(self, document_data: Document, user_id: str) -> Document:
        """
        Update document metadata.
        
        Args:
            document_data: Updated document data
            user_id: ID of the user updating the document
            
        Returns:
            Document: The updated document
        """
        document_id = document_data.id
        if not document_id:
            raise MyException(code=400, msg=_("Document ID is required for update"))
        
        with db.get_sync_session() as session:
            document = session.get(Document, document_id)
            if not document:
                raise MyException(code=404, msg=_("Document not found."))
                
            # Update allowed fields
            if document_data.filename:
                document.filename = document_data.filename
            if document_data.status:
                document.status = ProcessingStatus(document_data.status)
            if document_data.searchable_content:
                document.searchable_content = document_data.searchable_content
            # --- Start: Added field ---
            if document_data.recommendation:
                document.recommendation = document_data.recommendation
            # --- End: Added field ---

            document.updated_by = user_id
            document.updated_at = func.now()
            
            try:
                session.commit()
                session.refresh(document)
                make_transient(document)
                return document
            except IntegrityError as e:
                session.rollback()
                logger.error(f"Failed to update document: {e}")
                raise MyException(code=400, msg=_("Failed to update document. Please check the data and try again."))

    def delete_document(self, document_id: UUID, user_id: str) -> bool:
        """
        Delete a document and its OCR results.
        
        Args:
            document_id: ID of the document to delete
            user_id: ID of the user deleting the document
            
        Returns:
            bool: True if successful
        """
        
        with db.get_sync_session() as session:
            document = session.get(Document, document_id)
            if not document:
                raise MyException(code=404, msg=_("Document not found."))
                
            # Cascade delete will handle OCR results
            session.delete(document)
            
            try:
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete document: {e}")
                raise MyException(code=500, msg=_("Failed to delete document. Please try again later."))

    def change_document_status(self, document_id: UUID, new_status: ProcessingStatus, user_id: str) -> Document:
        """
        Change document processing status.
        
        Args:
            document_id: ID of the document
            new_status: New processing status
            user_id: ID of the user updating the status
            
        Returns:
            Document: The updated document
        """
        
        # Create a dictionary from the Document object to pass to update_document
        update_data = Document(id=document_id, status=new_status)
        return self.update_document(update_data, user_id)


    def get_document_by_id(self, document_id: UUID) -> Optional[Document]:
        """
        Get a document by its ID with OCR results.
        
        Args:
            document_id: ID of the document to retrieve
            
        Returns:
            Optional[Document]: Document with OCR results if found
        """
        if not document_id:
            return None

        print("get_document_by_id", document_id)
            
        with db.get_sync_session() as session:
            document = session.get(Document, document_id)
            if document:
                # Explicitly load OCR results
                document.ocr_results  # Load relationship
                make_transient(document)
            return document

    def list_documents(self, condition: DocumentList, user_id: str) -> tuple[List[Document], int]:
        """
        List documents with pagination and filtering.
        
        Args:
            condition: Query parameters including filters and pagination
            
        Returns:
            tuple: (list of documents, total count)
        """
        with db.get_sync_session() as session:
            # Base query
            query = select(Document)
            count_query = select(func.count()).select_from(Document)
            
            # Apply filters
            if condition.search_keywords:
                search = f"%{condition.search_keywords}%"
                query = query.where(or_(Document.filename.ilike(search), Document.searchable_content.ilike(search)))
                count_query = count_query.where(or_(Document.filename.ilike(search), Document.searchable_content.ilike(search)))
                
            if condition.status:
                status = ProcessingStatus(condition.status)
                query = query.where(Document.status == status)
                count_query = count_query.where(Document.status == status)
                
            if condition.from_time:
                query = query.where(Document.upload_timestamp >= condition.from_time)
                count_query = count_query.where(Document.upload_timestamp >= condition.from_time)
                
            if condition.to_time:
                query = query.where(Document.upload_timestamp <= condition.to_time)
                count_query = count_query.where(Document.upload_timestamp <= condition.to_time)
            
            # Apply sorting
            query = query.order_by(desc(Document.upload_timestamp))
            
            # Apply pagination
            page = condition.current if condition.current else 1
            page_size = condition.page_size if condition.page_size else 10
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            # Execute queries
            documents = session.scalars(query).all()
            total = session.scalar(count_query)
            
            # Make documents transient and load OCR results
            for doc in documents:
                # Load OCR results explicitly
                doc.ocr_results
                make_transient(doc)
                
            return documents, total

    def add_ocr_result(self, document_id: UUID, ocr_data: Dict[str, Any], user_id: str) -> OcrResult:
        """
        Add OCR result to a document.
        
        Args:
            document_id: ID of the document
            ocr_data: OCR result data
            user_id: ID of the user adding the result
            
        Returns:
            OcrResult: The created OCR result
        """
        required_fields = ['engine', 'extracted_text', 'processing_time_ms']
        if not all(field in ocr_data for field in required_fields):
            raise MyException(code=400, msg=_("Missing required OCR result fields"))
        
        with db.get_sync_session() as session:
            try:
                # Validate document exists
                document = session.get(Document, document_id)
                if not document:
                    raise MyException(code=404, msg=_("Document not found."))
                
                # Create OCR result
                ocr_result = OcrResult(
                    document_id=document_id,
                    engine=OcrEngine(ocr_data['engine']),
                    extracted_text=ocr_data['extracted_text'],
                    processing_time_ms=ocr_data['processing_time_ms'],
                    confidence_score=ocr_data.get('confidence_score'),
                    page_metrics=ocr_data.get('page_metrics'),
                    estimated_cost=ocr_data.get('estimated_cost'),
                    error_message=ocr_data.get('error_message'),
                    created_by=user_id,
                    updated_by=user_id
                )
                
                session.add(ocr_result)
                session.commit()
                session.refresh(ocr_result)
                
                # Update document status if needed
                if document.status != ProcessingStatus.completed and not ocr_data.get('error_message'):
                    document.status = ProcessingStatus.completed
                    document.updated_by = user_id
                    session.commit()
                
                return ocr_result
            except (ValueError, TypeError) as e:
                session.rollback()
                logger.error(f"Invalid OCR data: {e}")
                raise MyException(code=400, msg=_("Invalid OCR data format"))
            except IntegrityError as e:
                session.rollback()
                logger.error(f"Failed to add OCR result: {e}")
                raise MyException(code=400, msg=_("Failed to add OCR result. Please check the data and try again."))

    def parse_doc(self, document_id: UUID, user_id: str) -> Document:
        """
        Orchestrates OCR processing, generates recommendations, saves the results,
        and updates the document status.

        Args:
            document_id: The ID of the document to process.
            user_id: The ID of the user initiating the process.

        Returns:
            The updated document with its final status.
        """
        logger.info(f"Starting OCR parsing for document {document_id}")

        doc = self.get_document_by_id(document_id)
        if not doc or not doc.file_path:
            raise MyException(code=404, msg=_("Document not found."))
        storage_file_path = os.path.join(config.UPLOAD_FOLDER, doc.file_path)
        if not os.path.exists(storage_file_path):
            logger.error(f"Document file not found at path: {doc.file_path}")
            raise MyException(code=404, msg=_("Document file not found on server."))

        try:
            # 1. Set status to 'processing'
            self.change_document_status(document_id, ProcessingStatus.processing, user_id)

            # 2. Initialize and run OCR parser
            parser = OcrParser(engines=["easyocr", "paddleocr", "tesseract"])
            parse_output = parser.parse(storage_file_path)

            # 3. Aggregate results from the parser
            aggregated_results: Dict[str, Dict[str, Any]] = {}
            raw_results = []
            
            if 'results' in parse_output:
                raw_results.append(parse_output)
            elif 'page_results' in parse_output:
                raw_results.extend(parse_output['page_results'])

            for item in raw_results:
                for engine_name, ocr_result in item.get('results', {}).items():
                    if not isinstance(ocr_result, OcrParserResult):
                        continue
                    if engine_name not in aggregated_results:
                        aggregated_results[engine_name] = {"texts": [], "confidences": [], "processing_times_ms": [], "error_message": None}
                    
                    if ocr_result.metadata and ocr_result.metadata.get("error"):
                        aggregated_results[engine_name]["error_message"] = str(ocr_result.metadata["error"])
                        continue
                    
                    aggregated_results[engine_name]["texts"].append(ocr_result.text)
                    aggregated_results[engine_name]["confidences"].append(ocr_result.confidence)
                    aggregated_results[engine_name]["processing_times_ms"].append(ocr_result.processing_time_ms)

            # 4. Save aggregated OCR results to the database
            has_successful_ocr = False
            for engine, data in aggregated_results.items():
                if data["error_message"]:
                    ocr_data_to_save = {'engine': engine, 'extracted_text': '', 'processing_time_ms': sum(data.get("processing_times_ms", [0])), 'error_message': data["error_message"]}
                elif data["texts"]:
                    has_successful_ocr = True
                    avg_confidence = sum(data["confidences"]) / len(data["confidences"]) if data["confidences"] else 0
                    ocr_data_to_save = {'engine': engine, 'extracted_text': "\n\n".join(data["texts"]), 'processing_time_ms': int(sum(data["processing_times_ms"])), 'confidence_score': avg_confidence}
                else:
                    continue
                self.add_ocr_result(document_id, ocr_data_to_save, user_id)

            # 5. Build performance data for recommendation engine
            engine_performance = {}
            for engine, data in aggregated_results.items():
                if data["error_message"]: continue
                total_chars = len("\n\n".join(data["texts"]))
                total_time_ms = sum(data["processing_times_ms"])
                total_time_s = total_time_ms / 1000
                avg_confidence = sum(data["confidences"]) / len(data["confidences"]) if data["confidences"] else 0
                engine_performance[engine] = {'success_rate': 1.0, 'avg_confidence': avg_confidence, 'avg_processing_time_ms': total_time_ms, 'avg_chars_per_second': total_chars / total_time_s if total_time_s > 0 else 0, 'total_chars_extracted': total_chars}
            
            recommendation_summary = ""
            if engine_performance:
                # 6. Generate recommendation
                analyzer = OcrAnalyzer()
                recommendations = analyzer.generate_recommendations(engine_performance)
                recommendation_summary = recommendations.get("summary", "")

            # 7. Update document with best text and recommendation
            best_text = self._get_best_text_from_parse_output(parse_output, aggregated_results)
            if best_text or recommendation_summary:
                update_data = Document(id=document_id, searchable_content=best_text, recommendation=recommendation_summary)
                self.update_document(update_data, user_id)
            
            # 8. Set final document status
            final_status = ProcessingStatus.completed if has_successful_ocr else ProcessingStatus.failed
            updated_doc = self.change_document_status(document_id, final_status, user_id)
            
            logger.info(f"Successfully completed OCR processing for document {document_id}")
            return updated_doc

        except Exception as e:
            logger.error(f"Failed to parse document {document_id}: {e}")
            traceback.print_exc()
            self.change_document_status(document_id, ProcessingStatus.failed, user_id)
            raise MyException(code=500, msg=_("Failed to process document due to an internal server error."))

    def _get_best_text_from_parse_output(self, parse_output: Dict, aggregated_results: Dict) -> str:
        """Helper to extract the text from the best OCR result."""
        best_engine = None
        
        if 'best_result' in parse_output and parse_output['best_result']:
            best_engine = parse_output['best_result'].engine_name
        
        elif 'summary' in parse_output and parse_output.get('summary'):
            summary = parse_output['summary']
            best_engine_item = max(summary.items(), key=lambda item: item[1].get('avg_confidence', 0), default=None)
            if best_engine_item:
                best_engine = best_engine_item[0]

        if best_engine and best_engine in aggregated_results and aggregated_results[best_engine].get('texts'):
            return "\n\n".join(aggregated_results[best_engine]['texts'])
        
        return ""

    def export_parse_result(self, document_id: UUID, user_id: str) -> str:
        """
        Export parse results for a document to a CSV file.

        Args:
            document_id: ID of the document to export results for.
            user_id: ID of the user performing the export (for logging/auditing).

        Returns:
            str: The path to the generated CSV file.
        """
        logger.info(f"User {user_id} requested export for document {document_id}")

        document = self.get_document_by_id(document_id)
        if not document:
            raise MyException(code=404, msg=_("Document not found."))

        if not document.ocr_results:
            logger.warning(f"No OCR results found for document {document_id} to export.")
            raise MyException(code=404, msg=_("No OCR results to export for this document."))

        # Prepare the data for the CSV file by iterating through the OCR results
        results_data = []
        for result in document.ocr_results:
            results_data.append({
                'engine': result.engine.value if result.engine else None,
                'processing_time_ms': result.processing_time_ms,
                'confidence_score': result.confidence_score,
                'processed_at': result.processed_at.isoformat() if result.processed_at else None,
                'error_message': result.error_message,
                # Serialize the JSONB page_metrics field into a string
                'page_metrics': json.dumps(result.page_metrics) if result.page_metrics else None,
            })

        # Define the output directory and ensure it exists
        export_dir = config.EXPORT_DIR
        os.makedirs(export_dir, exist_ok=True)
        
        # Define the final path for the CSV file
        storage_file_path = os.path.join(export_dir, f"{document_id}_export.csv")

        # Create a pandas DataFrame and save it to a CSV file
        try:
            df = pd.DataFrame(results_data)
            df.to_csv(storage_file_path, index=False, encoding='utf-8')
            logger.info(f"Successfully exported OCR results for document {document_id} to {storage_file_path}")
        except Exception as e:
            logger.error(f"Failed to write CSV file for document {document_id}: {e}")
            raise MyException(code=500, msg=_("Failed to write export file."))

        return storage_file_path

    async def parse_doc_with_progress(self, websocket: WebSocket, document_id: UUID, user_id: str) -> Document:
        """
        Orchestrates OCR processing with real-time progress updates.
        """
        logger.info(f"Starting OCR parsing with progress for document {document_id}")
        
        doc = self.get_document_by_id(document_id)
        if not doc or not doc.file_path:
            await progress_manager.complete_progress(
                websocket, str(document_id), success=False, message="Document not found"
            )
            raise MyException(code=404, msg=_("Document not found."))
        
        storage_file_path = os.path.join(config.UPLOAD_FOLDER, doc.file_path)
        storage_file_path = os.path.abspath(storage_file_path)
        logger.info(f"Document file path: {storage_file_path}")
        if not os.path.exists(storage_file_path):
            await progress_manager.complete_progress(
                websocket, str(document_id), success=False, message="Document file not found on server"
            )
            raise MyException(code=404, msg=_("Document file not found on server."))

        try:
            # Step 1: Initialize (5%)
            await progress_manager.update_progress(
                websocket, str(document_id), "initializing", 1, 20, "Initializing OCR engines..."
            )
            
            # Set status to processing
            self.change_document_status(document_id, ProcessingStatus.processing, user_id)
            
            # Step 2: Setup (10%)
            await progress_manager.update_progress(
                websocket, str(document_id), "setup", 2, 20, "Setting up OCR parser..."
            )
            
            # Initialize parser with all available engines
            parser = OcrParser(
                engines=["easyocr", "paddleocr", "tesseract"],
                benchmark_mode=True,
                use_gpu=torch.cuda.is_available() if 'torch' in globals() else False
            )
            
            # Step 3: Start parsing (15%)
            await progress_manager.update_progress(
                websocket, str(document_id), "parsing", 3, 20, "Starting document parsing..."
            )
            
            # Create a modified parser that reports progress
            parse_output = await self._parse_with_progress_tracking(
                websocket, parser, storage_file_path, document_id
            )
            
            # Step 4: Processing results (80%)
            await progress_manager.update_progress(
                websocket, str(document_id), "processing_results", 16, 20, "Processing OCR results..."
            )
            
            # Process the new unified OCR output format
            aggregated_results = self._process_unified_ocr_output(parse_output)
            
            # Step 5: Saving results (85%)
            await progress_manager.update_progress(
                websocket, str(document_id), "saving_results", 17, 20, "Saving OCR results to database..."
            )
            
            has_successful_ocr = False  
            for engine, data in aggregated_results.items():
                if data.get("error_message"):
                    ocr_data_to_save = {
                        'engine': engine, 'extracted_text': '', 
                        'processing_time_ms': data.get("processing_time_ms", 0), 
                        'error_message': data["error_message"],
                        'confidence_score': 0.0,
                        'estimated_cost': 0.0
                    }
                elif data.get("text"):
                    has_successful_ocr = True
                    ocr_data_to_save = {
                        'engine': engine, 
                        'extracted_text': data["text"], 
                        'processing_time_ms': int(data.get("processing_time_ms", 0)), 
                        'confidence_score': data.get("confidence", 0.0),
                        'estimated_cost': data.get("estimated_cost", 0.0),
                        'page_metrics': {
                            'text_length': len(data["text"]),
                            'pages_processed': data.get("pages_processed", 1)
                        }
                    }
                else:
                    continue
                self.add_ocr_result(document_id, ocr_data_to_save, user_id)

            # Step 6: Generating recommendations (90%)
            await progress_manager.update_progress(
                websocket, str(document_id), "generating_recommendations", 18, 20, "Generating recommendations..."
            )
            
            recommendation_summary = self._generate_engine_recommendation(aggregated_results)

            # Step 7: Final updates (95%)
            await progress_manager.update_progress(
                websocket, str(document_id), "finalizing", 19, 20, "Finalizing document updates..."
            )
            
            best_text = self._get_best_text_from_unified_output(parse_output, aggregated_results)
            if best_text or recommendation_summary:
                update_data = Document(
                    id=document_id, 
                    searchable_content=best_text, 
                    recommendation=recommendation_summary
                )
                self.update_document(update_data, user_id)
            
            # Step 8: Complete (100%)
            final_status = ProcessingStatus.completed if has_successful_ocr else ProcessingStatus.failed
            updated_doc = self.change_document_status(document_id, final_status, user_id)
            
            # Notify completion
            success_message = f"OCR processing completed successfully with {len([e for e in aggregated_results.keys() if not aggregated_results[e].get('error_message')])} engines"
            await progress_manager.complete_progress(
                websocket, str(document_id), success=True, message=success_message
            )
            
            logger.info(f"Successfully completed OCR processing for document {document_id}")
            return updated_doc

        except Exception as e:
            logger.error(f"Failed to parse document {document_id}: {e}")
            traceback.print_exc()
            self.change_document_status(document_id, ProcessingStatus.failed, user_id)
            
            await progress_manager.complete_progress(
                websocket, str(document_id), success=False, message=f"Processing failed: {str(e)}"
            )
            
            raise MyException(code=500, msg=_("Failed to process document due to an internal server error."))

    async def _parse_with_progress_tracking(self, websocket: WebSocket, parser, file_path: str, document_id: UUID) -> Dict[str, Any]:
        """Parse document with progress tracking"""
        
        # Check if it's a PDF to determine total steps
        if file_path.lower().endswith('.pdf'):
            # For PDFs, we need to determine page count first
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    total_pages = len(pdf.pages)
                    
                await progress_manager.update_progress(
                    websocket, str(document_id), "parsing", 4, 20, f"Processing PDF with {total_pages} pages..."
                )
                
                # Track progress through parser
                result = await self._run_parser_with_page_progress(websocket, parser, file_path, document_id, total_pages)
                
            except Exception as e:
                logger.error(f"Error during PDF parsing: {e}")
                result = parser.parse(file_path)
        else:
            # Single image processing
            await progress_manager.update_progress(
                websocket, str(document_id), "parsing", 8, 20, "Processing image with OCR engines..."
            )
            result = parser.parse(file_path)
            
        return result
    
    async def _run_parser_with_page_progress(self, websocket: WebSocket, parser, file_path: str, document_id: UUID, total_pages: int):
        """Run parser with page-by-page progress updates"""
        # This is a simplified version - you'd need to modify your OcrParser
        # to accept progress callbacks or make it async
        
        base_progress = 4
        parsing_progress_range = 12  # Steps 4-15 are for parsing
        
        # Simulate progress updates during parsing
        for i in range(total_pages):
            progress_step = base_progress + int((i / total_pages) * parsing_progress_range)
            await progress_manager.update_progress(
                websocket, str(document_id), "parsing", 
                progress_step, 20, 
                f"Processing page {i+1} of {total_pages}..."
            )
        
        # Complete parsing phase
        await progress_manager.update_progress(
            websocket, str(document_id), "parsing", 15, 20, "Parsing completed, processing results..."
        )
        
        # Run the actual parser
        result = parser.parse(file_path)
        return result

    def _process_unified_ocr_output(self, parse_output: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Process the new unified OCR output format from OcrParser"""
        aggregated_results = {}
        
        if 'results' in parse_output:
            for engine_name, ocr_result in parse_output['results'].items():
                if hasattr(ocr_result, 'engine_name'):  # OCRResult object
                    aggregated_results[engine_name] = {
                        'text': ocr_result.text,
                        'confidence': ocr_result.confidence,
                        'processing_time_ms': ocr_result.processing_time_ms,
                        'estimated_cost': ocr_result.metadata.get('estimated_cost', 0.0) if ocr_result.metadata else 0.0,
                        'pages_processed': ocr_result.metadata.get('pages_processed', 1) if ocr_result.metadata else 1,
                        'error_message': ocr_result.metadata.get('error', None) if ocr_result.metadata else None
                    }
                else:
                    # Fallback for old format
                    aggregated_results[engine_name] = {
                        'text': str(ocr_result),
                        'confidence': 0.5,
                        'processing_time_ms': 0,
                        'estimated_cost': 0.0,
                        'pages_processed': 1,
                        'error_message': None
                    }
        
        return aggregated_results

    def _get_best_text_from_unified_output(self, parse_output: Dict[str, Any], aggregated_results: Dict[str, Dict[str, Any]]) -> str:
        """Extract the best text from the unified OCR output format"""
        if 'best_result' in parse_output and parse_output['best_result']:
            best_result = parse_output['best_result']
            if hasattr(best_result, 'text'):
                return best_result.text
            elif isinstance(best_result, dict):
                return best_result.get('text', '')
        
        # Fallback: find the result with highest confidence
        if aggregated_results:
            best_engine = max(aggregated_results.items(), 
                            key=lambda x: x[1].get('confidence', 0) if not x[1].get('error_message') else 0,
                            default=(None, {}))[0]
            if best_engine:
                return aggregated_results[best_engine].get('text', '')
        
        return ""

    def _generate_engine_recommendation(self, aggregated_results: Dict[str, Dict[str, Any]]) -> str:
        """Generate a recommendation based on engine performance"""
        if not aggregated_results:
            return "No OCR engines were able to process this document."
        
        # Filter out failed engines
        successful_engines = {k: v for k, v in aggregated_results.items() 
                            if not v.get('error_message') and v.get('text')}
        
        if not successful_engines:
            return "All OCR engines failed to process this document."
        
        # Score each engine
        engine_scores = {}
        for engine_name, data in successful_engines.items():
            confidence = data.get('confidence', 0.0)
            speed = 1.0 / (1.0 + data.get('processing_time_ms', 1000) / 1000)  # Normalize to seconds
            cost_efficiency = 1.0 / (1.0 + data.get('estimated_cost', 0.0) * 100)
            
            # Weighted scoring
            score = confidence * 0.5 + speed * 0.3 + cost_efficiency * 0.2
            engine_scores[engine_name] = score
        
        # Find best engine
        best_engine = max(engine_scores.items(), key=lambda x: x[1])[0]
        best_data = successful_engines[best_engine]
        
        # Generate recommendation
        recommendation = f"Recommendation: {best_engine.upper()} performed best with "
        recommendation += f"{best_data.get('confidence', 0.0):.1%} confidence, "
        recommendation += f"{best_data.get('processing_time_ms', 0)/1000:.2f}s processing time, "
        recommendation += f"and ${best_data.get('estimated_cost', 0.0):.4f} estimated cost."
        
        return recommendation

    def search_documents(self, search_query: str, user_id: str, limit: int = 50, offset: int = 0) -> Tuple[List[Document], int]:
        """
        Search documents by text content, filename, or OCR results.
        
        Args:
            search_query: Text to search for
            user_id: ID of the user performing the search
            limit: Maximum number of results to return
            offset: Number of results to skip for pagination
            
        Returns:
            Tuple of (documents, total_count)
        """
        with db.get_sync_session() as session:
            try:
                # Build search query using SQLAlchemy
                query = select(Document).where(
                    Document.created_by == user_id
                )
                
                if search_query.strip():
                    search_term = f"%{search_query.strip()}%"
                    query = query.where(
                        or_(
                            Document.filename.ilike(search_term),
                            Document.searchable_content.ilike(search_term),
                            Document.recommendation.ilike(search_term)
                        )
                    )
                
                # Get total count
                count_query = select(func.count()).select_from(query.subquery())
                total_count = session.execute(count_query).scalar()
                
                # Get paginated results
                query = query.order_by(desc(Document.upload_timestamp)).offset(offset).limit(limit)
                documents = session.execute(query).scalars().all()
                
                return documents, total_count
                
            except Exception as e:
                logger.error(f"Search failed: {e}")
                raise MyException(code=500, msg=_("Search operation failed."))

    def get_ocr_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get OCR processing statistics for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing OCR statistics
        """
        with db.get_sync_session() as session:
            try:
                # Get basic counts
                total_docs = session.execute(
                    select(func.count(Document.id)).where(Document.created_by == user_id)
                ).scalar()
                
                completed_docs = session.execute(
                    select(func.count(Document.id)).where(
                        Document.created_by == user_id,
                        Document.status == ProcessingStatus.completed
                    )
                ).scalar()
                
                failed_docs = session.execute(
                    select(func.count(Document.id)).where(
                        Document.created_by == user_id,
                        Document.status == ProcessingStatus.failed
                    )
                ).scalar()
                
                # Get engine performance stats
                engine_stats = session.execute(
                    select(
                        OcrResult.engine,
                        func.avg(OcrResult.confidence_score).label('avg_confidence'),
                        func.avg(OcrResult.processing_time_ms).label('avg_time'),
                        func.count(OcrResult.id).label('total_processed')
                    ).join(Document).where(
                        Document.created_by == user_id,
                        Document.status == ProcessingStatus.completed
                    ).group_by(OcrResult.engine)
                ).fetchall()
                
                # Get recent processing times
                recent_times = session.execute(
                    select(OcrResult.processing_time_ms).join(Document).where(
                        Document.created_by == user_id,
                        Document.status == ProcessingStatus.completed
                    ).order_by(desc(OcrResult.processed_at)).limit(10)
                ).scalars().all()
                
                return {
                    'total_documents': total_docs or 0,
                    'completed_documents': completed_docs or 0,
                    'failed_documents': failed_docs or 0,
                    'success_rate': (completed_docs / total_docs * 100) if total_docs else 0,
                    'engine_performance': [
                        {
                            'engine': stat.engine.value,
                            'avg_confidence': float(stat.avg_confidence or 0),
                            'avg_processing_time_ms': float(stat.avg_time or 0),
                            'total_processed': stat.total_processed
                        }
                        for stat in engine_stats
                    ],
                    'recent_processing_times': recent_times
                }
                
            except Exception as e:
                logger.error(f"Failed to get OCR statistics: {e}")
                raise MyException(code=500, msg=_("Failed to retrieve OCR statistics."))