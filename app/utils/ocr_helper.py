import os
from typing import Dict, Union, List, Any

import pytesseract
from PIL import Image
from core.extends_logger import logger

# Import OCR engines conditionally to handle missing dependencies gracefully
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import azure.ai.vision as azure_vision
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


class OCRHelper:
    """Helper class for performing OCR on images with multiple backend options.
    
    Supports:
    - Tesseract OCR (default)
    - EasyOCR
    - Azure OCR (requires API key)
    
    Features:
    - Confidence scoring
    - Multi-language support
    - Fallback mechanisms
    """

    def __init__(self, method: str = "tesseract", 
             languages: List[str] = None,
             azure_key: str = None,
             azure_endpoint: str = None,
             **kwargs):
        """Initialize OCR helper with selected backend
        
        Args:
            method: OCR method/engine to use
            languages: List of language codes to support
            azure_key: Azure API key (required for azure method)
            azure_endpoint: Azure endpoint URL (required for azure method)
            **kwargs: Additional parameters for specific OCR engines
        """
        self.method = method.lower()
        self.languages = languages or ["en", "ch"]
        self.engine = None
        self.kwargs = kwargs
        
        # Configure selected OCR engine
        if self.method == "tesseract":
            # No initialization needed for tesseract
            pass
            
        elif self.method == "easyocr":
            if not EASYOCR_AVAILABLE:
                logger.warning("EasyOCR not installed. Falling back to Tesseract.")
                self.method = "tesseract"
            else:
                # Map language codes to EasyOCR supported languages
                easyocr_lang_map = {
                    "en": "en",
                    "ch": "ch_sim",  # Map 'ch' to 'ch_sim' for simplified Chinese
                    "chinese": "ch_sim",
                    "jp": "ja",  # Japanese code in EasyOCR is 'ja'
                    "japanese": "ja",
                    "ko": "ko",
                    "korean": "ko",
                    "fr": "fr",
                    "french": "fr",
                    "de": "de",
                    "german": "de",
                    "it": "it",
                    "italian": "it",
                    "es": "es",
                    "spanish": "es",
                    "pt": "pt",
                    "portuguese": "pt",
                    "ru": "ru",
                    "russian": "ru",
                    "ar": "ar",
                    "arabic": "ar",
                    "hi": "hi",
                    "hindi": "hi"
                }
                
                # Convert language codes for EasyOCR
                easyocr_langs = []
                for lang in self.languages:
                    if lang.lower() in easyocr_lang_map:
                        easyocr_langs.append(easyocr_lang_map[lang.lower()])
                    else:
                        # Keep as-is if no mapping exists
                        easyocr_langs.append(lang.lower())
                
                # Initialize EasyOCR with mapped languages
                logger.info(f"Initializing EasyOCR with languages: {easyocr_langs}")
                try:
                    self.engine = easyocr.Reader(easyocr_langs, **kwargs)
                except Exception as e:
                    logger.error(f"Error initializing EasyOCR: {str(e)}")
                    self.method = "tesseract"
            
        elif self.method == "azure":
            if not AZURE_AVAILABLE:
                logger.warning("Azure Vision SDK not installed. Falling back to Tesseract.")
                self.method = "tesseract"
            elif not azure_key or not azure_endpoint:
                logger.warning("Azure API key or endpoint not provided. Falling back to Tesseract.")
                self.method = "tesseract"
            else:
                # Initialize Azure OCR client
                try:
                    self.azure_key = azure_key
                    self.azure_endpoint = azure_endpoint
                    # We'll create the service on-demand to avoid unnecessary connections
                    self.engine = "configured"
                except Exception as e:
                    logger.error(f"Error initializing Azure OCR: {str(e)}")
                    self.method = "tesseract"
        else:
            logger.warning(f"Unknown OCR method: {method}. Using Tesseract.")
            self.method = "tesseract"
        
        logger.info(f"OCR Helper initialized with method: {self.method}")

    def extract_text(self, image_path: str, 
                     return_confidence: bool = False, 
                     return_details: bool = False) -> Union[str, Dict[str, Any]]:
        """Extract text from an image using the configured OCR engine
        
        Args:
            image_path: Path to the image file
            return_confidence: Whether to return confidence score
            return_details: Whether to return detailed OCR results
            
        Returns:
            String with extracted text or dict with text and metadata
        """
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return "" if not return_confidence and not return_details else {"text": "", "confidence": 0}
        
        result = {"text": "", "confidence": 0, "details": []}
        
        try:
            # Log detailed results
            logger.debug(f"OCR method: {self.method}")
            
            if self.method == "tesseract":
                result = self._extract_with_tesseract(image_path)
                
            elif self.method == "easyocr":
                result = self._extract_with_easyocr(image_path)
        
            elif self.method == "azure":
                result = self._extract_with_azure(image_path)
                
            else:
                # Fallback to tesseract if method is unknown
                result = self._extract_with_tesseract(image_path)
                
        except Exception as e:
            logger.error(f"Error extracting text with {self.method}: {str(e)}")
            # Return empty result on error
            result = {"text": "", "confidence": 0, "details": []}
        
        # Format return value based on flags
        if return_confidence and return_details:
            return result
        elif return_confidence:
            return {"text": result["text"], "confidence": result["confidence"]}
        elif return_details:
            return {"text": result["text"], "details": result["details"]}
        else:
            return result["text"]

    def _extract_with_tesseract(self, image_path: str) -> Dict[str, Any]:
        """Extract text using Tesseract OCR
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            image = Image.open(image_path)
            
            # Determine language string for tesseract
            lang_str = "+".join(self._map_languages_to_tesseract())
            
            # Get detailed data for confidence calculation
            data = pytesseract.image_to_data(image, lang=lang_str, output_type=pytesseract.Output.DICT)
            
            # Extract text
            text = pytesseract.image_to_string(image, lang=lang_str)
            
            # Calculate average confidence
            confidences = [float(conf) for conf in data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            avg_confidence = avg_confidence / 100.0  # Normalize to 0-1 range
            
            # Collect detailed results
            details = []
            for i in range(len(data['text'])):
                if data['text'][i].strip():
                    details.append({
                        'text': data['text'][i],
                        'confidence': float(data['conf'][i]) / 100 if data['conf'][i] != '-1' else 0,
                        'box': [data['left'][i], data['top'][i], 
                               data['left'][i] + data['width'][i], 
                               data['top'][i] + data['height'][i]]
                    })
            return {
                "text": text.strip(),
                "confidence": avg_confidence,
                "details": details
            }
        except Exception as e:
            logger.error(f"Tesseract OCR error: {str(e)}")
            return {"text": "", "confidence": 0, "details": []}

    def _extract_with_easyocr(self, image_path: str) -> Dict[str, Any]:
        """Extract text using EasyOCR
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        if not self.engine or not EASYOCR_AVAILABLE:
            return self._extract_with_tesseract(image_path)
            
        try:
            # Get detailed results
            detailed_results = self.engine.readtext(image_path)
            
            # Extract text and calculate confidence
            text_parts = []
            confidences = []
            details = []
            
            for result in detailed_results:
                bbox, text, confidence = result
                text_parts.append(text)
                confidences.append(confidence)
                details.append({
                    'text': text,
                    'confidence': confidence,
                    'box': [coord for point in bbox for coord in point]  # Flatten bbox
                })
            
            full_text = "\n".join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "text": full_text,
                "confidence": avg_confidence,
                "details": details
            }
        except Exception as e:
            logger.error(f"EasyOCR error: {str(e)}")
            return {"text": "", "confidence": 0, "details": []}

    def _extract_with_azure(self, image_path: str) -> Dict[str, Any]:
        """Extract text using Azure Computer Vision
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        if not AZURE_AVAILABLE or self.engine != "configured":
            return self._extract_with_tesseract(image_path)
            
        try:
            # Create Azure client
            service_options = azure_vision.VisionServiceOptions(self.azure_endpoint, self.azure_key)
            vision_source = azure_vision.VisionSource(image_path)
            
            # Analyze image
            analysis_options = azure_vision.ImageAnalysisOptions()
            analysis_options.features = (
                azure_vision.ImageAnalysisFeature.CAPTION |
                azure_vision.ImageAnalysisFeature.TEXT
            )
            
            image_analyzer = azure_vision.ImageAnalyzer(service_options, vision_source, analysis_options)
            result = image_analyzer.analyze()
            
            if result.reason == azure_vision.ImageAnalysisResultReason.ANALYZED:
                # Extract text from results
                text_parts = []
                details = []
                
                if result.text is not None:
                    for line in result.text.lines:
                        text_parts.append(line.content)
                        # Azure doesn't provide per-line confidence scores
                        details.append({
                            'text': line.content,
                            'confidence': 0.9,  # Azure doesn't provide this, using high default
                            'box': [line.bounding_polygon[0], line.bounding_polygon[1], 
                                   line.bounding_polygon[4], line.bounding_polygon[5]]
                        })
                
                full_text = "\n".join(text_parts)
                
                return {
                    "text": full_text,
                    "confidence": 0.9,  # Azure doesn't provide this, using high default
                    "details": details
                }
            else:
                logger.warning(f"Azure analyze error: {result.error.message}")
                return {"text": "", "confidence": 0, "details": []}
                
        except Exception as e:
            logger.error(f"Azure OCR error: {str(e)}")
            return {"text": "", "confidence": 0, "details": []}

    def _map_languages_to_tesseract(self) -> List[str]:
        """Map language codes to Tesseract language codes
        
        Returns:
            List of Tesseract language codes
        """
        # Simple mapping of common language codes
        tesseract_map = {
            "en": "eng",
            "ch": "chi_sim",
            "chinese": "chi_sim",
            "jp": "jpn",
            "japanese": "jpn",
            "ko": "kor",
            "korean": "kor",
            "fr": "fra",
            "french": "fra",
            "de": "deu",
            "german": "deu",
            "it": "ita",
            "italian": "ita",
            "es": "spa",
            "spanish": "spa",
            "pt": "por",
            "portuguese": "por",
            "ru": "rus",
            "russian": "rus",
            "ar": "ara",
            "arabic": "ara",
            "hi": "hin",
            "hindi": "hin"
        }
        
        tesseract_langs = []
        for lang in self.languages:
            if lang.lower() in tesseract_map:
                tesseract_langs.append(tesseract_map[lang.lower()])
            else:
                # If no mapping found, use as-is
                tesseract_langs.append(lang.lower())
                
        return tesseract_langs if tesseract_langs else ["eng"]