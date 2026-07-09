"""Typed shapes for the Plainlode live-scan data layer.

These are plain data containers. The trends client fills TrendPoint/TermSeries
from the Scrapingdog pull; the ranker (a later step) fills the slope/direction/
rising/rank fields on Finding. Nothing here makes an LLM call.
"""

from dataclasses import dataclass, field


@dataclass
class TrendPoint:
    """One interest-over-time sample for a single query."""
    date: str
    timestamp: int
    value: int


@dataclass
class TermSeries:
    """The full interest-over-time series for one query term at one geo."""
    query: str
    geo: str
    points: list[TrendPoint]


@dataclass
class Finding:
    """One term's series plus the ranker's read of it.

    slope/direction/rising/rank are left at their defaults by the data layer
    and filled in by the ranker in a later step.
    """
    query: str
    series: TermSeries
    slope: float = 0.0
    direction: str = ""
    rising: bool = False
    low_volume: bool = False
    rank: int = 0
    reason: str = ""  # one-line tag from the cheap-tier filter model
    supply: dict | None = None  # Amazon supply signal (top findings only), or None


@dataclass
class ScanResult:
    """The output of one scan: every term's finding, tagged with provenance."""
    geo: str
    pulled_at: str  # ISO 8601
    source: str
    findings: list[Finding] = field(default_factory=list)
    category: str = ""  # the scan's vertical, used by the briefing layer
