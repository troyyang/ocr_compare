# ocr_analyzer.py
from typing import Dict, Any

class OcrAnalyzer:
    """
    Analyzes OCR engine performance data to generate comparisons and recommendations.
    This logic is shared between the benchmark script and the document service.
    """

    def _estimate_cost_per_page(self, engine_name: str, avg_time_ms: float) -> float:
        """
        Estimate cost per page for different engines.
        These are rough estimates and should be updated with real pricing.
        """
        cost_models = {
            'tesseract': 0.0,
            'easyocr': 0.0,
            'paddleocr': 0.0,
            'pdfplumber': 0.0,  # Digital extractor, not a priced OCR engine
            'azure': 0.001,
            'google': 0.0015,
            'aws': 0.001
        }
        base_cost = cost_models.get(engine_name.lower(), 0.0)
        
        # Add a computational cost estimate for self-hosted solutions
        if base_cost == 0.0 and avg_time_ms > 0:
            compute_cost = (avg_time_ms / 1000) * 0.0001  # e.g., $0.0001 per second
            return compute_cost
            
        return base_cost

    def _get_engine_strengths(self, stats: Dict) -> str:
        """Identify an engine's main strengths based on its stats."""
        strengths = []
        if stats.get('avg_confidence', 0) > 0.9:
            strengths.append("high accuracy")
        if stats.get('avg_chars_per_second', 0) > 1000:
            strengths.append("fast processing")
        if stats.get('estimated_cost_per_page', 1) == 0:
            strengths.append("zero cost")
        if stats.get('success_rate', 0) > 0.95:
            strengths.append("high reliability")
        
        return ", ".join(strengths) if strengths else "adequate performance"

    def _generate_recommendation_summary(self, performance: Dict, scores: Dict) -> str:
        """Generate a user-friendly markdown summary of recommendations."""
        if not performance or not scores:
            return "Insufficient data for recommendations."
        
        best_engine = max(scores.items(), key=lambda x: x[1])[0]
        best_stats = performance[best_engine]
        
        summary_lines = [
            f"## OCR Engine Recommendation",
            f"",
            f"**Winner: {best_engine.upper()}**",
            f"",
            f"Based on a comparison of {len(performance)} engines, **{best_engine}** offers the best overall performance for this document:",
            f"- Confidence: {best_stats.get('avg_confidence', 0):.1%}",
            f"- Speed: {best_stats.get('avg_chars_per_second', 0):.0f} chars/second",
            f"- Success Rate: {best_stats.get('success_rate', 0):.1%}",
            f"- Est. Cost/Page: ${best_stats.get('estimated_cost_per_page', 0):.4f}",
            f"",
            f"### Trade-offs:",
        ]
        
        sorted_engines = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        for i, (engine, score) in enumerate(sorted_engines):
            stats = performance[engine]
            if i == 0:
                summary_lines.append(f"1. **{engine}** (Recommended): Best overall balance.")
            else:
                summary_lines.append(f"{i+1}. **{engine}**: A good alternative, offering {self._get_engine_strengths(stats)}.")
        
        return "\n".join(summary_lines)

    def generate_recommendations(self, engine_performance: Dict) -> Dict[str, Any]:
        """
        Generate recommendations from a dictionary of engine performance stats.
        
        Args:
            engine_performance: A dictionary where keys are engine names and values
                                are dicts of performance metrics.
                                
        Returns:
            A dictionary containing detailed recommendations and a summary.
        """
        if not engine_performance:
            return {}

        # Add estimated cost to performance data
        for engine, stats in engine_performance.items():
            stats['estimated_cost_per_page'] = self._estimate_cost_per_page(
                engine, stats.get('avg_processing_time_ms', 0)
            )

        # Find best engines for different criteria
        best_accuracy = max(engine_performance.items(), key=lambda x: x[1].get('avg_confidence', 0), default=(None, {}))
        best_speed = max(engine_performance.items(), key=lambda x: x[1].get('avg_chars_per_second', 0), default=(None, {}))
        best_cost = min(engine_performance.items(), key=lambda x: x[1].get('estimated_cost_per_page', float('inf')), default=(None, {}))
        best_reliability = max(engine_performance.items(), key=lambda x: x[1].get('success_rate', 0), default=(None, {}))
        
        # Calculate overall scores using a weighted formula
        overall_scores = {}
        for engine, stats in engine_performance.items():
            score = (
                stats.get('avg_confidence', 0) * 0.4 +
                min(stats.get('avg_chars_per_second', 0) / 1000, 1.0) * 0.3 +
                stats.get('success_rate', 0) * 0.2 +
                (1.0 - min(stats.get('estimated_cost_per_page', 0) * 1000, 1.0)) * 0.1
            )
            overall_scores[engine] = score
        
        if not overall_scores:
            return {"summary": "No valid engine data to generate recommendations."}

        best_overall = max(overall_scores.items(), key=lambda x: x[1])
        
        recommendations = {
            'best_accuracy': {'engine': best_accuracy[0], 'confidence': best_accuracy[1].get('avg_confidence')},
            'best_speed': {'engine': best_speed[0], 'chars_per_second': best_speed[1].get('avg_chars_per_second')},
            'best_cost': {'engine': best_cost[0], 'cost_per_page': best_cost[1].get('estimated_cost_per_page')},
            'best_reliability': {'engine': best_reliability[0], 'success_rate': best_reliability[1].get('success_rate')},
            'best_overall': {'engine': best_overall[0], 'score': best_overall[1]},
        }
        recommendations['summary'] = self._generate_recommendation_summary(engine_performance, overall_scores)
        return recommendations