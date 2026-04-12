"""
Numeric Data Detector Utility

Context-aware detection of meaningful numeric data in PDF text.
Used to conditionally enable/disable chart generation across all PDFs.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Keywords that, when near a number, indicate meaningful data
_DATA_KEYWORDS = [
    "revenue", "sales", "growth", "users", "emissions", "cost", "budget",
    "profit", "loss", "income", "expenditure", "margin", "rate", "total",
    "average", "median", "count", "volume", "capacity", "population",
    "score", "rating", "index", "ratio", "yield", "output", "input",
    "production", "consumption", "demand", "supply", "market", "share",
    "gdp", "inflation", "unemployment", "export", "import", "debt",
    "investment", "return", "dividend", "asset", "liability", "equity",
    "funding", "valuation", "benchmark", "target", "forecast", "estimate",
    "increase", "decrease", "decline", "rise", "drop", "surge", "reduction",
    "million", "billion", "trillion", "thousand", "mn", "bn", "cr", "lakh",
    "breakdown", "distribution", "allocation", "comparison", "benchmark",
]

# Patterns to IGNORE (noise)
_NOISE_PATTERNS = [
    re.compile(r"\bPage\s+\d+\b", re.IGNORECASE),
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),        # Phone numbers
    re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}\b"),      # ISO timestamps
    re.compile(r"\b[A-Z0-9]{8,}-[A-Z0-9]{4,}\b"),             # UUID-like IDs
    re.compile(r"ISBN[\s:-]?\d"),                               # ISBNs
    re.compile(r"\bID[\s:#]?\s?\d+\b", re.IGNORECASE),        # Generic IDs
]

# Visualization intent keywords
_VIZ_KEYWORDS = [
    "chart", "graph", "plot", "visualize", "visualization", "visualise",
    "diagram", "bar chart", "pie chart", "line chart", "area chart",
    "show me data", "table of data", "show data", "display data",
    "create a chart", "generate a chart", "draw a chart", "make a chart",
    "data visualization", "data visualisation",
]

# Chart type indicators
_PIE_KEYWORDS = ["percent", "proportion", "share", "breakdown", "distribution", "composition", "%"]
_LINE_KEYWORDS = ["monthly", "yearly", "quarterly", "annual", "over time", "trend", "timeline", "year-over-year", "yoy", "growth rate"]
_BAR_KEYWORDS = ["comparison", "compare", "by region", "by department", "by category", "ranking", "top", "vs", "versus"]


def _clean_text(text: str) -> str:
    """Remove known noise patterns from text before scoring."""
    cleaned = text
    for pattern in _NOISE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned


def has_numeric_data(text: str) -> tuple:
    """
    Context-aware numeric data detection using a scoring system.
    
    Returns:
        (bool, int): (has_data, score) — True if score >= threshold.
    
    Scoring:
        - Number near a meaningful keyword: +3
        - Standalone percentage (45%, 0.67%): +2
        - Currency value ($1.2M, €500, ₹10k): +2
        - Tabular separator (|) with numbers: +2
        - Comparison language near numbers: +2
    
    Threshold: score >= 4
    """
    THRESHOLD = 4
    score = 0
    details = []

    cleaned = _clean_text(text)
    text_lower = cleaned.lower()

    # 1. Numbers near meaningful keywords (+3 each, cap at 5 matches)
    keyword_hits = 0
    for keyword in _DATA_KEYWORDS:
        # Look for keyword within ~60 chars of a number
        pattern = re.compile(
            rf"(?:\b{re.escape(keyword)}\b.{{0,60}}\d+\.?\d*|\d+\.?\d*.{{0,60}}\b{re.escape(keyword)}\b)",
            re.IGNORECASE
        )
        matches = pattern.findall(cleaned)
        if matches:
            keyword_hits += len(matches)
            score += 3 * len(matches)
            details.append(f"keyword '{keyword}': {len(matches)} hits (+{3 * len(matches)})")
            if keyword_hits >= 5:
                break

    # 2. Standalone percentages (+2 each, cap at 5)
    pct_matches = re.findall(r"\b\d+\.?\d*\s*%", cleaned)
    if pct_matches:
        count = min(len(pct_matches), 5)
        score += 2 * count
        details.append(f"percentages: {count} found (+{2 * count})")

    # 3. Currency values (+2 each, cap at 5)
    currency_matches = re.findall(r"[\$€£₹¥]\s*\d[\d,]*\.?\d*\s*[MBKmkbTt]?\b", cleaned)
    if currency_matches:
        count = min(len(currency_matches), 5)
        score += 2 * count
        details.append(f"currency: {count} found (+{2 * count})")

    # 4. Tabular data — lines with | separators containing numbers (+2)
    table_lines = re.findall(r"^.*\|.*\d+.*\|.*$", cleaned, re.MULTILINE)
    if len(table_lines) >= 2:
        score += 2
        details.append(f"table rows: {len(table_lines)} found (+2)")

    # 5. Comparison language near numbers (+2)
    comparison_patterns = [
        r"(?:increased|decreased|rose|fell|dropped|surged|declined|grew)\s+(?:by|from|to)\s+\d",
        r"\d+\.?\d*\s*(?:more|less|higher|lower|greater|fewer)\s+than",
        r"over\s+time[:\s]+\w+\s+\d+",
    ]
    for cp in comparison_patterns:
        if re.search(cp, cleaned, re.IGNORECASE):
            score += 2
            details.append(f"comparison language found (+2)")
            break

    passed = score >= THRESHOLD
    logger.info(f"[NumericDetector] Score: {score}/{THRESHOLD} → {'PASS' if passed else 'FAIL'} | {'; '.join(details) if details else 'no indicators'}")
    return (passed, score)


def user_requests_visualization(query: str) -> bool:
    """Check if user explicitly asks for a chart, graph, or visualization."""
    query_lower = query.lower()
    result = any(kw in query_lower for kw in _VIZ_KEYWORDS)
    logger.info(f"[NumericDetector] Visualization intent: {result} for query: '{query[:80]}...'")
    return result


def detect_chart_type(text: str) -> str:
    """
    Analyze text context to suggest the optimal chart type.
    
    Returns: "pie", "bar", or "line" (defaults to "bar").
    """
    text_lower = text.lower()

    pie_score = sum(1 for kw in _PIE_KEYWORDS if kw in text_lower)
    line_score = sum(1 for kw in _LINE_KEYWORDS if kw in text_lower)
    bar_score = sum(1 for kw in _BAR_KEYWORDS if kw in text_lower)

    scores = {"pie": pie_score, "line": line_score, "bar": bar_score}
    best = max(scores, key=scores.get)

    # Heuristic adjustment: Only pick non-bar if it clearly wins by a margin
    # or if bar has a very low score.
    if scores[best] == 0:
        return "bar"
    
    if best == "pie" and scores["pie"] <= (scores["bar"] + 1):
        return "bar"
    
    if best == "line" and scores["line"] <= scores["bar"]:
        return "bar"

    logger.info(f"[NumericDetector] Chart type suggestion: {best} (pie={pie_score}, line={line_score}, bar={bar_score})")
    return best
