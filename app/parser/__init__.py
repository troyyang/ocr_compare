import os
from abc import ABC, abstractmethod
from typing import Type, Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DocumentElement:
    """Data class for document elements with consistent structure"""
    type: str
    content: str
    y0: float
    x0: float = 0
    metadata: Optional[Dict] = None


@dataclass
class OCRResult:
    """Standardized OCR result format for comparison"""
    engine_name: str
    text: str
    confidence: float
    processing_time_ms: float
    page_num: int
    metadata: Optional[Dict] = None


class BaseParser(ABC):
    """Abstract base class for all file parsers"""
    
    @abstractmethod
    def parse(self, file_path: str) -> str:
        """Parse the file and return parsed file path in Markdown format"""
        pass

from .ocr_parser import OcrParser
from .ocr_analyzer import OcrAnalyzer
from .ocr_benchmark import OCRBenchmark

# Export public API
__all__ = [
    'BaseParser',
    'ParserFactory',
    'DocumentElement',
    'OCRResult',
    'OcrParser',
    'OCRBenchmark',
    'OcrAnalyzer'
]

class ParserFactory:
    """Factory class for creating appropriate parsers"""
    
    _parsers: Dict[str, Type[BaseParser]] = {}
    
    @classmethod
    def register_parser(cls, file_ext: str, parser: Type[BaseParser]):
        """Register a parser for specific file extension"""
        cls._parsers[file_ext.lower()] = parser
        
    @classmethod
    def get_parser(cls, file_path: str, output_dir: str=None) -> BaseParser:
        """Get appropriate parser based on file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        parser_class = cls._parsers.get(ext)
        if not output_dir:
            output_dir = "data/parse/output"
            
        if not parser_class:
            raise ValueError(f"No parser registered for {ext} files")
        return parser_class(output_dir=output_dir)


# Register with factory
ParserFactory.register_parser('.pdf', OcrParser)
ParserFactory.register_parser('.jpg', OcrParser)
ParserFactory.register_parser('.jpeg', OcrParser)
ParserFactory.register_parser('.png', OcrParser)