import os
import re
import torch
import shutil
import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Union, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from PIL import Image as PILImage

# PDF processing
import pdfplumber
from pdf2image import convert_from_path

# Register with factory
from . import BaseParser, DocumentElement, OCRResult
from utils.ocr_helper import OCRHelper

# Configure logging
logger = logging.getLogger(__name__)

class OcrParser(BaseParser):
    """Enhanced PDF/Image parser with multi-engine OCR support
    
    Features:
    1. Support for multiple OCR engines (EasyOCR, PaddleOCR, Tesseract)
    2. Unified interface for engine comparison
    3. Performance benchmarking and confidence tracking
    4. Support for both PDF and image inputs
    5. Structured output for analysis
    """

    def __init__(self, output_dir: str = "data/parse/output", 
                 engines: List[str] = None,
                 scanned_threshold: float = 0.3,
                 max_workers: int = 2,
                 use_gpu: bool = True,
                 benchmark_mode: bool = False):
        """Initialize the enhanced parser
        
        Args:
            output_dir: Directory to store output files and images
            engines: List of OCR engines to use for comparison
            scanned_threshold: Threshold to determine if a page is scanned (0-1)
            max_workers: Maximum number of parallel workers
            use_gpu: Whether to use GPU acceleration when available
            benchmark_mode: Enable detailed benchmarking and comparison
        """
        self.output_dir = Path(output_dir)
        self.image_dir = self.output_dir / "images"
        self.image_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.scanned_threshold = scanned_threshold
        self.max_workers = max_workers
        self.benchmark_mode = benchmark_mode
        self.use_gpu = use_gpu and torch.cuda.is_available()
        
        # Initialize OCR engines for comparison
        self.engines = engines or ["easyocr", "tesseract"]  # Default engines
        self.ocr_engines = {}
        self._initialize_engines()
        
        # Results storage for comparison
        self.ocr_results: List[OCRResult] = []
        
        self._init_regex_patterns()
        logger.info(f"OcrParser initialized with engines: {list(self.ocr_engines.keys())}")

    def _initialize_engines(self) -> None:
        """Initialize all requested OCR engines"""
        for engine_name in self.engines:
            try:
                if engine_name.lower() == "paddleocr":
                    # Initialize PaddleOCR if available
                    try:
                        from paddleocr import PaddleOCR
                        self.ocr_engines["paddleocr"] = PaddleOCR(
                            use_angle_cls=True, 
                            lang='en',
                            use_gpu=self.use_gpu
                        )
                        logger.info("PaddleOCR initialized successfully")
                    except ImportError:
                        logger.warning("PaddleOCR not available, skipping")
                        
                elif engine_name.lower() == "easyocr":
                    # Initialize EasyOCR
                    self.ocr_engines["easyocr"] = OCRHelper(
                        method="easyocr",
                        languages=["en", "ch"],
                        use_gpu=self.use_gpu
                    )
                    logger.info("EasyOCR initialized successfully")
                    
                elif engine_name.lower() == "tesseract":
                    # Initialize Tesseract
                    self.ocr_engines["tesseract"] = OCRHelper(
                        method="tesseract",
                        languages=["en", "ch"]
                    )
                    logger.info("Tesseract initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize {engine_name}: {str(e)}")

    def _init_regex_patterns(self) -> None:
        """Compile regex patterns for text cleaning"""
        self.multi_newline = re.compile(r"\n{3,}")
        self.whitespace = re.compile(r" {2,}")
        self.page_break = re.compile(r"\- \d+ \-")

    def parse(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Main parsing workflow with multi-engine comparison
        
        Args:
            file_path: Path to the PDF or image file to parse
            
        Returns:
            A unified dictionary containing parsing results and metadata.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Parsing file: {file_path}")
        
        # Determine file type and process accordingly
        if file_path.suffix.lower() == '.pdf':
            return self._parse_pdf(file_path)
        elif file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            return self._parse_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    def _parse_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Parse PDF with multi-engine OCR comparison"""
        try:
            # Detect scanned pages
            is_scanned, scanned_pages = self._detect_scanned_document(pdf_path)
            
            # If any page is scanned, treat the whole document with OCR for simplicity
            if is_scanned or len(scanned_pages) > 0:
                logger.info(f"Processing PDF with {len(scanned_pages)} scanned pages using OCR")
                return self._process_pdf_with_ocr(pdf_path, scanned_pages)
            else:
                logger.info("Processing digital PDF")
                return self._process_digital_pdf(pdf_path)
                
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path}: {str(e)}")
            raise

    def _parse_image(self, image_path: Path) -> Dict[str, Any]:
        """Parse single image with all OCR engines and return unified format"""
        logger.info(f"Processing image: {image_path}")
        
        # Process with all available engines
        results = {}
        
        for engine_name, engine in self.ocr_engines.items():
            start_time = datetime.now()
            
            try:
                if engine_name == "paddleocr":
                    ocr_result = self._run_paddleocr(engine, str(image_path))
                else:
                    ocr_result = engine.extract_text(
                        str(image_path), 
                        return_confidence=True
                    )
                
                # Standardize result format
                if isinstance(ocr_result, dict):
                    text = ocr_result.get("text", "")
                    confidence = ocr_result.get("confidence", 0)
                else:
                    text = ocr_result
                    confidence = 0.5  # Default confidence
                
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                
                result = OCRResult(
                    engine_name=engine_name, text=text, confidence=confidence,
                    processing_time_ms=processing_time, page_num=1,
                    metadata={
                        "file_path": str(image_path), "file_size": image_path.stat().st_size,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                results[engine_name] = result
                self.ocr_results.append(result)
                
            except Exception as e:
                logger.error(f"Error with {engine_name} on {image_path}: {str(e)}")
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                results[engine_name] = OCRResult(
                    engine_name=engine_name, text="", confidence=0.0,
                    processing_time_ms=processing_time, page_num=1, metadata={"error": str(e)}
                )
        
        # Build the unified output
        best_result = self._select_best_result(results)
        summary = self._generate_comparison_data(results)

        return {
            "file_path": str(image_path),
            "file_type": "image",
            "processing_method": "ocr",
            "total_pages": 1,
            "results": results,
            "best_result": best_result,
            "summary": summary
        }

    def _process_pdf_with_ocr(self, pdf_path: Path, scanned_pages: List[int]) -> Dict[str, Any]:
        """Process PDF pages requiring OCR and return unified format"""
        page_results_by_engine: Dict[str, List[OCRResult]] = {name: [] for name in self.ocr_engines}

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = scanned_pages if scanned_pages else list(range(total_pages))
            
            images = convert_from_path(pdf_path, dpi=200)

            for i, page_num in enumerate(pages_to_process):
                logger.info(f"Processing page {page_num + 1}/{total_pages}")
                img = images[page_num]
                img_path = self.image_dir / f"page_{page_num + 1}.jpg"
                img.save(img_path, "JPEG", quality=95)
                
                page_result = self._process_page_with_engines(img_path, page_num + 1)
                for engine_name, result in page_result.get("results", {}).items():
                    page_results_by_engine[engine_name].append(result)
        
        # Aggregate results from all pages for each engine
        aggregated_results: Dict[str, OCRResult] = {}
        for engine_name, results_list in page_results_by_engine.items():
            if not results_list:
                continue
            
            full_text = "\n\n".join([res.text for res in results_list if res.text])
            total_time = sum(res.processing_time_ms for res in results_list)
            avg_confidence = sum(res.confidence for res in results_list) / len(results_list) if results_list else 0
            
            # Create a single aggregated OCRResult for the whole document for this engine
            aggregated_results[engine_name] = OCRResult(
                engine_name=engine_name, text=full_text,
                confidence=avg_confidence, processing_time_ms=total_time,
                page_num=total_pages, # Represents all pages
                metadata={"pages_processed": len(results_list)}
            )

        best_result = self._select_best_result(aggregated_results)
        summary = self._generate_comparison_data(aggregated_results)

        return {
            "file_path": str(pdf_path),
            "file_type": "pdf",
            "processing_method": "ocr",
            "total_pages": total_pages,
            "results": aggregated_results,
            "best_result": best_result,
            "summary": summary
        }

    def _process_digital_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Process digital PDF and return unified format"""
        start_time = datetime.now()
        elements = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    elements.append(DocumentElement(
                        type="text", content=text.strip(), y0=page.bbox[1],
                        metadata={"page_num": page_num + 1}
                    ))
                try:
                    for i, table in enumerate(page.find_tables()):
                        table_data = table.extract()
                        if table_data:
                            df = pd.DataFrame(table_data[1:], columns=table_data[0])
                            markdown_table = df.to_markdown(index=False)
                            elements.append(DocumentElement(
                                type="table", content=markdown_table, y0=page.bbox[1],
                                metadata={"page_num": page_num + 1, "table_index": i}
                            ))
                except Exception as e:
                    logger.warning(f"Table extraction error on page {page_num + 1}: {str(e)}")

        markdown_content = self._generate_markdown(elements)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Create a "pseudo" OCRResult to fit the unified structure
        digital_result = OCRResult(
            engine_name="pdfplumber", text=markdown_content,
            confidence=1.0, # Confidence is 100% for direct extraction
            processing_time_ms=processing_time, page_num=total_pages
        )

        results = {"pdfplumber": digital_result}
        
        return {
            "file_path": str(pdf_path),
            "file_type": "pdf",
            "processing_method": "digital_extraction",
            "total_pages": total_pages,
            "results": results,
            "best_result": digital_result, # The best result is the only result
            "summary": self._generate_comparison_data(results)
        }

    def _process_page_with_engines(self, img_path: Path, page_num: int) -> Dict[str, Any]:
        """Process single page with all OCR engines"""
        results = {}
        
        for engine_name, engine in self.ocr_engines.items():
            start_time = datetime.now()
            
            try:
                if engine_name == "paddleocr":
                    ocr_result = self._run_paddleocr(engine, str(img_path))
                else:
                    ocr_result = engine.extract_text(
                        str(img_path), 
                        return_confidence=True
                    )
                
                # Standardize result
                if isinstance(ocr_result, dict):
                    text = ocr_result.get("text", "")
                    confidence = ocr_result.get("confidence", 0)
                else:
                    text = ocr_result
                    confidence = 0.5
                
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                
                result = OCRResult(
                    engine_name=engine_name, text=text, confidence=confidence,
                    processing_time_ms=processing_time, page_num=page_num
                )
                
                results[engine_name] = result
                self.ocr_results.append(result) # For benchmarking
                
            except Exception as e:
                logger.error(f"Error with {engine_name} on page {page_num}: {str(e)}")
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                results[engine_name] = OCRResult(
                    engine_name=engine_name, text="", confidence=0.0,
                    processing_time_ms=processing_time, page_num=page_num,
                    metadata={"error": str(e)}
                )
        
        return {
            "page_num": page_num,
            "results": results,
            "best_result": self._select_best_result(results)
        }

    def _run_paddleocr(self, paddle_engine, image_path: str) -> Dict[str, Any]:
        """Run PaddleOCR and format results"""
        try:
            result = paddle_engine.ocr(image_path, cls=True)
            
            if not result or not result[0]:
                return {"text": "", "confidence": 0}
            
            texts, confidences = [], []
            for line in result[0]:
                if len(line) >= 2:
                    texts.append(line[1][0])
                    confidences.append(float(line[1][1]))
            
            combined_text = "\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {"text": combined_text, "confidence": avg_confidence}
            
        except Exception as e:
            logger.error(f"PaddleOCR error: {str(e)}")
            return {"text": "", "confidence": 0}

    def _detect_scanned_document(self, pdf_path: Path) -> Tuple[bool, List[int]]:
        """Detect if PDF pages are scanned"""
        scanned_pages = []
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages: return False, []
            total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                # A page is likely scanned if it has very few text characters but contains images.
                if len(text.strip()) < 100 and page.images:
                    scanned_pages.append(page_num)
            
            scanned_ratio = len(scanned_pages) / total_pages
            return scanned_ratio >= self.scanned_threshold, scanned_pages

    def _select_best_result(self, results: Dict[str, OCRResult]) -> Optional[OCRResult]:
        """Select the best OCR result based on confidence and text length"""
        if not results: return None
            
        valid_results = [r for r in results.values() if r and r.text]
        if not valid_results:
            # Return the first available result even if it's an error, for traceability
            return next(iter(results.values()), None)

        # Score each result
        scored_results = []
        for result in valid_results:
            score = (
                result.confidence * 0.8 +  # Confidence is the most important factor
                min(len(result.text) / 2000, 1.0) * 0.2  # Text length is a secondary factor
            )
            scored_results.append((score, result))
        
        return max(scored_results, key=lambda x: x[0])[1] if scored_results else None

    def _generate_comparison_data(self, results: Dict[str, OCRResult]) -> Dict[str, Any]:
        """Generate comparison data for benchmarking"""
        if not results: return {}
            
        valid_results = [r for r in results.values() if r]
        count = len(valid_results)
        if count == 0: return {}
            
        return {
            "engine_count": len(results),
            "avg_confidence": sum(r.confidence for r in valid_results) / count,
            "avg_processing_time": sum(r.processing_time_ms for r in valid_results) / count,
            "text_lengths": {name: len(r.text) for name, r in results.items()},
            "confidences": {name: r.confidence for name, r in results.items()},
            "processing_times": {name: r.processing_time_ms for name, r in results.items()}
        }

    # ... (Helper methods _generate_markdown, _save_markdown_file, benchmarking methods remain unchanged) ...
    def _generate_markdown(self, elements: List[DocumentElement]) -> str:
        if not elements: return ""
        markdown = []
        current_page = 0
        for element in elements:
            page_num = element.metadata.get("page_num", 0) if element.metadata else 0
            if page_num > current_page:
                markdown.append(f"\n\n## Page {page_num}\n\n")
                current_page = page_num
            if element.type == "text":
                markdown.append(element.content)
            elif element.type == "table":
                markdown.append(f"\n\n{element.content}\n\n")
        return "\n".join(markdown)

    def _save_markdown_file(self, source_path: Path, content: str) -> str:
        filename = f"{source_path.stem}_converted.md"
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(output_path)
    
    def get_benchmark_results(self) -> pd.DataFrame:
        if not self.ocr_results: return pd.DataFrame()
        data = [{
            "engine": r.engine_name, "page_num": r.page_num, "text_length": len(r.text),
            "confidence": r.confidence, "processing_time_ms": r.processing_time_ms
        } for r in self.ocr_results]
        return pd.DataFrame(data)

    def export_benchmark_results(self, output_path: str = None) -> str:
        if not output_path:
            output_path = self.output_dir / "benchmark_results.csv"
        df = self.get_benchmark_results()
        df.to_csv(output_path, index=False)
        logger.info(f"Benchmark results exported to {output_path}")
        return str(output_path)