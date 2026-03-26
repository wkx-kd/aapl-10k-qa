"""Load and parse the aapl_10k.json data file."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Section category mapping
SECTION_CATEGORIES = {
    1: "introduction",
    2: "business",
    3: "risk",
    4: "other",
    5: "cybersecurity",
    6: "properties",
    7: "legal",
    8: "other",
    9: "market",
    10: "other",
    11: "mda",
    12: "market_risk",
    13: "financial",
    14: "other",
    15: "controls",
    16: "other",
    17: "other",
    18: "governance",
    19: "compensation",
    20: "ownership",
    21: "other",
    22: "other",
    23: "exhibits",
    24: "other",
    25: "financial_table",
    26: "financial_table",
    27: "financial_table",
    28: "other",
}


def load_records(data_path: str) -> list[dict]:
    """Load records from aapl_10k.json.

    The JSON has a SQL query string as the top-level key,
    with the value being the array of records.
    """
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract records from the SQL-query-keyed dict
    key = list(data.keys())[0]
    records = data[key]

    logger.info(f"Loaded {len(records)} records from {data_path}")

    # Enrich with category
    for record in records:
        sid = record.get("section_id", 0)
        record["section_category"] = SECTION_CATEGORIES.get(sid, "other")

    return records


def get_records_by_year(records: list[dict]) -> dict[int, list[dict]]:
    """Group records by fiscal year."""
    by_year: dict[int, list[dict]] = {}
    for r in records:
        year = r["file_fiscal_year"]
        by_year.setdefault(year, []).append(r)
    return by_year


def get_available_years(records: list[dict]) -> list[int]:
    """Get sorted list of available fiscal years."""
    return sorted(set(r["file_fiscal_year"] for r in records))


def get_section_types(records: list[dict]) -> list[dict]:
    """Get unique section types with their IDs and categories."""
    seen = set()
    sections = []
    for r in records:
        key = (r["section_id"], r["section_title"])
        if key not in seen:
            seen.add(key)
            sections.append({
                "section_id": r["section_id"],
                "section_title": r["section_title"],
                "section_category": r.get("section_category", "other"),
            })
    return sorted(sections, key=lambda x: x["section_id"])
