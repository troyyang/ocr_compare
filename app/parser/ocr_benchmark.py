#!/usr/bin/env python3
"""
OCR Engine Benchmark Script
"""

import os
from glob import glob
from tqdm import tqdm
import json
import argparse
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Union
import logging
from datetime import datetime
import time

from .ocr_parser import OcrParser, OCRResult
from .ocr_analyzer import OcrAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OCRBenchmark:
    """Benchmark multiple OCR engines on a collection of documents"""
    
    def __init__(self,
                 engines: List[str] = None,
                 output_dir: str = "benchmark_results",
                 use_gpu: bool = True):
        """Initialize benchmark suite"""
        self.engines = engines or ["easyocr", "paddleocr", "tesseract"]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.parser = OcrParser(output_dir=str(self.output_dir), engines=self.engines, use_gpu=use_gpu, benchmark_mode=True)
        self.analyzer = OcrAnalyzer()  # Use the shared analyzer

        self.results = []
        self.summary_stats = {}

    def _find_files(self, input_path: Path, file_extensions: List[str]) -> List[Path]:
        """Discover files in a directory, potentially recursively, or return a single file."""
        if input_path.is_file():
            if input_path.suffix.lower() in file_extensions:
                return [input_path]
            else:
                raise ValueError(f"File {input_path} has an unsupported extension. Supported: {file_extensions}")
        elif input_path.is_dir():
            found_files = []
            for ext in file_extensions:
                # search in subdirectories as well
                found_files.extend(input_path.rglob(f"*{ext.lower()}"))
                found_files.extend(input_path.rglob(f"*{ext.upper()}"))
            return sorted(list(set(found_files))) # Remove duplicates and sort for consistent order
        else:
            raise FileNotFoundError(f"Input path is neither a file nor a directory: {input_path}")


    def run_benchmark(self, input_path: Union[str, Path], file_extensions: List[str] = None) -> Dict[str, Any]:
        """Run benchmark on a single file or all files in an input directory (including subdirectories)."""
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input path not found: {input_path}")

        # Default file extensions
        if file_extensions is None:
            file_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']

        # Find all test files based on input_path type
        test_files = self._find_files(input_path, file_extensions)

        if not test_files:
            raise ValueError(f"No supported files found at {input_path} with extensions {file_extensions}")

        logger.info(f"Found {len(test_files)} test files")
        logger.info(f"Benchmarking engines: {self.engines}")

        # Process each file with a progress bar
        # Wrap test_files with tqdm to show progress
        for i, file_path in enumerate(tqdm(test_files, desc="Processing Documents")): # <--- Modified line
            logger.info(f"Processing {i+1}/{len(test_files)}: {file_path.name}") # Keep original logging for detailed output

            try:
                start_time = time.time()
                # The parse method in OcrParser already returns the unified dictionary
                result = self.parser.parse(file_path)
                total_time = time.time() - start_time

                # Extract results for analysis
                file_result = {
                    'file_name': file_path.name,
                    'file_path': str(file_path),
                    'file_size': file_path.stat().st_size,
                    'file_type': file_path.suffix.lower(),
                    'total_processing_time': total_time,
                    'engines': {}
                }

                # Now, the 'results' key directly contains the OCRResult objects for each engine
                # regardless of whether it's a single image or aggregated PDF pages.
                for engine_name, ocr_result in result.get('results', {}).items():
                    file_result['engines'][engine_name] = self._extract_engine_metrics(ocr_result)

                self.results.append(file_result)

            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {str(e)}")
                # Add error result
                file_result = {
                    'file_name': file_path.name,
                    'file_path': str(file_path),
                    'file_size': file_path.stat().st_size,
                    'file_type': file_path.suffix.lower(),
                    'total_processing_time': 0,
                    'error': str(e),
                    'engines': {}
                }
                self.results.append(file_result)

        # Generate analysis
        analysis = self._analyze_results()

        # Save results
        self._save_results(analysis)

        return analysis
    
    def _extract_engine_metrics(self, ocr_result: OCRResult) -> Dict[str, Any]:
        """Extract standardized metrics from OCR result"""
        # ... (This method's implementation remains unchanged) ...
        return {
            'text_length': len(ocr_result.text),
            'confidence': ocr_result.confidence,
            'processing_time_ms': ocr_result.processing_time_ms,
            'text_snippet': ocr_result.text[:300] + ('...' if len(ocr_result.text) > 300 else ''),
            'chars_per_second': len(ocr_result.text) / (ocr_result.processing_time_ms / 1000) if ocr_result.processing_time_ms > 0 else 0
        }

    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze benchmark results and generate statistics using the shared analyzer."""
        if not self.results:
            return {}
        
        engine_stats, file_type_stats = {}, {}
        total_files_processed, successful_files = 0, 0
        
        for result in self.results:
            if 'error' in result: continue
            total_files_processed += 1
            if result['engines']: successful_files += 1
            
            file_type = result['file_type']
            file_type_stats.setdefault(file_type, {'count': 0, 'total_size': 0})['count'] += 1
            file_type_stats[file_type]['total_size'] += result['file_size']
            
            for engine_name, metrics in result['engines'].items():
                stats = engine_stats.setdefault(engine_name, {'total_files': 0, 'total_chars': 0, 'total_time': 0, 'confidences': [], 'speeds': [], 'successful_extractions': 0})
                stats['total_files'] += 1
                stats['total_chars'] += metrics['text_length']
                stats['total_time'] += metrics['processing_time_ms']
                stats['confidences'].append(metrics.get('confidence', metrics.get('avg_confidence', 0))) # Handle both result types
                stats['speeds'].append(metrics.get('chars_per_second', 0))
                if metrics['text_length'] > 0: stats['successful_extractions'] += 1

        summary = {'overview': {'total_files': len(self.results), 'files_processed': total_files_processed, 'successful_files': successful_files, 'success_rate': successful_files / total_files_processed if total_files_processed > 0 else 0, 'engines_tested': list(engine_stats.keys()), 'timestamp': datetime.now().isoformat()}, 'engine_performance': {}, 'file_type_breakdown': {}}
        
        for file_type, stats in file_type_stats.items():
            summary['file_type_breakdown'][file_type] = {'file_count': stats['count'], 'avg_file_size_mb': (stats['total_size'] / stats['count']) / (1024 * 1024), 'total_size_mb': stats['total_size'] / (1024 * 1024)}
        
        engine_performance = {}
        for engine_name, stats in engine_stats.items():
            if stats['total_files'] == 0: continue
            engine_performance[engine_name] = {
                'files_processed': stats['total_files'],
                'success_rate': stats['successful_extractions'] / stats['total_files'],
                'avg_confidence': sum(stats['confidences']) / len(stats['confidences']) if stats['confidences'] else 0,
                'avg_processing_time_ms': stats['total_time'] / stats['total_files'],
                'avg_chars_per_second': sum(stats['speeds']) / len(stats['speeds']) if stats['speeds'] else 0,
                'total_chars_extracted': stats['total_chars'],
            }
        
        # Use the shared analyzer to generate recommendations
        summary['engine_performance'] = engine_performance
        summary['recommendations'] = self.analyzer.generate_recommendations(engine_performance)
        
        return summary

    # Note: _generate_recommendations, _estimate_cost_per_page, etc., have been removed
    # as their logic is now in the OcrAnalyzer class.
    
    def _save_results(self, analysis: Dict[str, Any]) -> None:
        """Save benchmark results to files"""
        # ... (This method's implementation remains unchanged) ...
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results as JSON
        results_file = self.output_dir / f"benchmark_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'results': self.results,
                'analysis': analysis
            }, f, indent=2, default=str)
        
        # Save CSV summary for easy analysis
        csv_data = []
        for result in self.results:
            if 'error' in result:
                continue
                
            base_row = {
                'file_name': result['file_name'],
                'file_type': result['file_type'],
                'file_size_mb': result['file_size'] / (1024 * 1024),
                'total_time_s': result['total_processing_time']
            }
            
            for engine_name, metrics in result['engines'].items():
                row = base_row.copy()
                row.update({
                    'engine': engine_name,
                    'text_length': metrics['text_length'],
                    'confidence': metrics.get('confidence', metrics.get('avg_confidence')),
                    'processing_time_ms': metrics['processing_time_ms'],
                    'chars_per_second': metrics.get('chars_per_second', 0)
                })
                csv_data.append(row)
        
        if csv_data:
            df = pd.DataFrame(csv_data)
            csv_file = self.output_dir / f"benchmark_summary_{timestamp}.csv"
            df.to_csv(csv_file, index=False)
        
        # Save markdown report
        self._save_markdown_report(analysis, timestamp)
        
        logger.info(f"Results saved to {self.output_dir}")

    def _save_markdown_report(self, analysis: Dict, timestamp: str) -> None:
        """Save a formatted markdown report"""
        report_file = self.output_dir / f"benchmark_report_{timestamp}.md"
        
        overview = analysis['overview']
        lines = [
            "# OCR Engine Benchmark Report", f"", f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"",
            "## Overview", f"", f"- **Total files processed:** {overview['total_files']}", f"- **Successful processes:** {overview['successful_files']}",
            f"- **Success rate:** {overview['success_rate']:.1%}", f"- **Engines tested:** {', '.join(overview['engines_tested'])}", f"",
            "## Engine Performance Comparison", f"", "| Engine | Confidence | Speed (chars/s) | Success Rate | Cost/Page |", "|--------|------------|----------------|--------------|-----------|"
        ]
        
        engine_performance = analysis.get('engine_performance', {})
        for engine, stats in engine_performance.items():
            lines.append(f"| {engine} | {stats.get('avg_confidence', 0):.1%} | {stats.get('avg_chars_per_second', 0):.0f} | {stats.get('success_rate', 0):.1%} | ${stats.get('estimated_cost_per_page', 0.0):.4f} |")
        
        if 'recommendations' in analysis and 'summary' in analysis['recommendations']:
            lines.extend(["", analysis['recommendations']['summary']])
        
        with open(report_file, 'w') as f:
            f.write('\n'.join(lines))
    
    @classmethod
    def run_from_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the OCR benchmark based on a provided configuration dictionary.
        This method serves as a convenient entry point for CLI or other scripts.
        """
        input_path = config.get('input_path')
        output_dir = config.get('output_dir', 'benchmark_results')
        engines = config.get('engines')
        extensions = config.get('extensions')
        use_gpu = config.get('use_gpu', True)

        if not input_path:
            raise ValueError("Input path must be specified in the configuration.")

        benchmark = cls(engines=engines, output_dir=output_dir, use_gpu=use_gpu)
        logger.info(f"Starting benchmark from config on {input_path}")
        return benchmark.run_benchmark(input_path, extensions)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Benchmark OCR engines on document collections')
    parser.add_argument('--input-dir', help='Directory containing test documents')
    parser.add_argument('--input-file', help='Path to a single test document') # New argument for single file
    parser.add_argument('--output-dir', default='benchmark_results', help='Output directory for results')
    parser.add_argument('--engines', nargs='+', default=['easyocr', 'paddleocr', 'tesseract'],
                       help='OCR engines to benchmark')
    parser.add_argument('--extensions', nargs='+', default=['.pdf', '.jpg', '.png'],
                       help='File extensions to process')
    parser.add_argument('--no-gpu', action='store_true', help='Disable GPU acceleration')
    parser.add_argument('--config', help='JSON config file with benchmark settings')

    args = parser.parse_args()

    # Load config if provided
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config) as f:
            config = json.load(f)

    # Override config with CLI arguments if present
    if args.input_dir:
        config['input_path'] = args.input_dir
    elif args.input_file: # Prioritize input_file if both are given in CLI
        config['input_path'] = args.input_file
    if args.output_dir != 'benchmark_results': # Only override if default was changed
        config['output_dir'] = args.output_dir
    if args.engines != ['easyocr', 'paddleocr', 'tesseract']: # Only override if default was changed
        config['engines'] = args.engines
    if args.extensions != ['.pdf', '.jpg', '.png']: # Only override if default was changed
        config['extensions'] = args.extensions
    if args.no_gpu:
        config['use_gpu'] = False

    # Ensure input_path is set either from CLI or config
    if 'input_path' not in config:
        parser.error("Either --input-dir, --input-file, or 'input_path' in a config file must be provided.")

    try:
        # Run benchmark using the new run_from_config method
        logger.info(f"Starting benchmark with config: {config}")
        results = OCRBenchmark.run_from_config(config)

        # Print summary
        print("\n" + "="*60)
        print("BENCHMARK COMPLETE")
        print("="*60)

        if 'recommendations' in results and 'best_overall' in results['recommendations']:
            best = results['recommendations']['best_overall']
            print(f"Best Engine: {best['engine'].upper()}")
            print(f"Overall Score: {best['score']:.3f}")

        print(f"\nDetailed results saved to: {config.get('output_dir', 'benchmark_results')}")

    except Exception as e:
        logger.error(f"Benchmark failed: {str(e)}")
        raise