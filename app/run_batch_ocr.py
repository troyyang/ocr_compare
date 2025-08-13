# run_batch_ocr.py
import argparse
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from parser.ocr_benchmark import OCRBenchmark

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description='Batch process documents using OCR engines and generate a performance report.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # Removed --config argument
    parser.add_argument(
        '--input-path',
        type=str,
        required=True, # Make input_path required since there's no config to fall back on
        help='Path to a single document file or a directory containing documents.'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='benchmark_results', # Set default here
        help='Directory to save benchmark results.'
    )
    parser.add_argument(
        '--engines',
        nargs='+',
        default=['easyocr', 'paddleocr', 'tesseract'], # Set default here
        help='Space-separated list of OCR engines to use (e.g., easyocr paddleocr tesseract).'
    )
    parser.add_argument(
        '--extensions',
        nargs='+',
        default=['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp'], # Set default here
        help='Space-separated list of file extensions to process (e.g., .pdf .jpg .png).'
    )
    parser.add_argument(
        '--no-gpu',
        action='store_true',
        help='Disable GPU acceleration for OCR engines.'
    )

    args = parser.parse_args()

    # Construct the config dictionary directly from argparse arguments
    # Defaults are now handled by argparse directly or within OCRBenchmark's __init__
    config = {
        'input_path': args.input_path,
        'output_dir': args.output_dir,
        'engines': args.engines,
        'extensions': args.extensions,
        'use_gpu': not args.no_gpu # Set use_gpu based on --no-gpu flag
    }

    # Input path is now required by argparse, so no need for manual check here.

    try:
        # Run the benchmark using the run_from_config class method
        logger.info("Starting OCR benchmark...")
        logger.info(f"Benchmark parameters: {config}")
        benchmark_results = OCRBenchmark.run_from_config(config)
        logger.info("OCR benchmark completed.")

        # Print summary of the best engine
        if 'recommendations' in benchmark_results and 'best_overall' in benchmark_results['recommendations']:
            best = benchmark_results['recommendations']['best_overall']
            print("\n" + "="*60)
            print("OCR BENCHMARK SUMMARY")
            print("="*60)
            print(f"**Best Performing Engine:** {best['engine'].upper()} (Overall Score: {best['score']:.3f})")
            print(f"\nDetailed reports (CSV, JSON, Markdown) are saved in: {Path(config['output_dir']).resolve()}")
            print("="*60)
        else:
            print("\n" + "="*60)
            print("OCR BENCHMARK COMPLETED WITH NO RECOMMENDATIONS (Insufficient data).")
            print("="*60)

    except FileNotFoundError as e:
        logger.error(f"File or directory not found: {e}")
        exit(1)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        exit(1)
    except ImportError as e:
        logger.error(f"Missing dependency for OCR engine: {e}. Please ensure all required OCR libraries are installed.")
        logger.error("For example, for PaddleOCR: pip install paddleocr; for EasyOCR: pip install easyocr; for Tesseract: install tesseract-ocr and pip install pytesseract.")
        exit(1)
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
        exit(1)

if __name__ == '__main__':
    main()