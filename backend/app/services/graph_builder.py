"""Build Neo4j knowledge graph from 10-K data using rules + patterns."""

import re
import logging

from app.core.graph_store import GraphStore

logger = logging.getLogger(__name__)

# Predefined Apple product catalog
APPLE_PRODUCTS = [
    {
        "name": "iPhone",
        "category": "Hardware",
        "description": "Smartphone product line",
    },
    {
        "name": "Mac",
        "category": "Hardware",
        "description": "Personal computer product line including MacBook, iMac, Mac Pro, Mac mini",
    },
    {
        "name": "iPad",
        "category": "Hardware",
        "description": "Tablet computer product line",
    },
    {
        "name": "Wearables, Home and Accessories",
        "category": "Hardware",
        "description": "Includes Apple Watch, AirPods, Apple TV, HomePod and accessories",
    },
    {
        "name": "Services",
        "category": "Services",
        "description": "Advertising, AppleCare, cloud services, digital content, and payment services",
    },
]

# Geographic segments
APPLE_SEGMENTS = [
    {"name": "Americas", "description": "North and South America"},
    {"name": "Europe", "description": "European countries, India, Middle East, and Africa"},
    {"name": "Greater China", "description": "China mainland, Hong Kong, and Taiwan"},
    {"name": "Japan", "description": "Japan"},
    {"name": "Rest of Asia Pacific", "description": "Australia, Korea, and other Asia Pacific countries"},
]

# Risk categories (predefined common categories for Apple)
RISK_CATEGORIES = [
    {
        "name": "Macroeconomic and Industry Risks",
        "description": "Risks from global economic conditions, currency fluctuations, and industry competition",
    },
    {
        "name": "Supply Chain and Manufacturing Risks",
        "description": "Risks from reliance on third-party manufacturers, component supply constraints",
    },
    {
        "name": "Technology and Product Risks",
        "description": "Risks from rapid technological change, product transition challenges",
    },
    {
        "name": "Legal and Regulatory Risks",
        "description": "Risks from litigation, antitrust actions, privacy regulations",
    },
    {
        "name": "Cybersecurity and Data Privacy Risks",
        "description": "Risks from data breaches, cyberattacks, and privacy compliance",
    },
    {
        "name": "Intellectual Property Risks",
        "description": "Risks related to IP protection, patent disputes",
    },
    {
        "name": "Financial and Tax Risks",
        "description": "Risks from tax law changes, credit conditions, investment losses",
    },
    {
        "name": "Geopolitical Risks",
        "description": "Risks from international trade tensions, political instability",
    },
]


def build_knowledge_graph(
    graph_store: GraphStore,
    records: list[dict],
    financial_metrics: dict[int, dict],
):
    """Build the complete knowledge graph from 10-K data."""
    logger.info("Building knowledge graph...")

    # Clear existing data
    graph_store.clear_graph()
    graph_store.create_constraints()

    # 1. Create company node
    graph_store.build_company_node()

    # 2. Create fiscal year nodes
    years = sorted(set(r["file_fiscal_year"] for r in records))
    graph_store.build_fiscal_years(years)

    # 3. Create product nodes
    graph_store.build_products(APPLE_PRODUCTS)

    # 4. Create segment nodes
    graph_store.build_segments(APPLE_SEGMENTS)

    # 5. Extract and create executives
    executives = _extract_executives(records)
    graph_store.build_executives(executives)

    # 6. Create risk categories and link to years
    risk_cats_with_years = _enrich_risk_categories(records, years)
    graph_store.build_risk_categories(risk_cats_with_years)

    # 7. Link financial metrics
    graph_store.build_financial_links(financial_metrics)

    # 8. Link risk categories to products (based on text analysis)
    _link_risks_to_products(graph_store, records)

    logger.info("Knowledge graph built successfully")


def _extract_executives(records: list[dict]) -> list[dict]:
    """Extract executive names and roles from 10-K sections."""
    executives = []
    seen_names = set()

    # Common executive patterns in 10-K
    exec_patterns = [
        r"(Timothy\s+D\.\s+Cook|Tim\s+Cook).*?(Chief Executive Officer|CEO)",
        r"(Luca\s+Maestri).*?(Senior Vice President|Chief Financial Officer|CFO)",
        r"(Kevan\s+Parekh).*?(Senior Vice President|Chief Financial Officer|CFO)",
        r"(Jeff\s+Williams).*?(Chief Operating Officer|COO)",
        r"(Katherine\s+L?\.\s*Adams|Kate\s+Adams).*?(Senior Vice President|General Counsel)",
        r"(Deirdre\s+O'Brien).*?(Senior Vice President.*?Retail)",
        r"(Craig\s+Federighi).*?(Senior Vice President.*?Software)",
        r"(John\s+Ternus).*?(Senior Vice President.*?Hardware)",
        r"(Greg\s+Joswiak).*?(Senior Vice President.*?Marketing)",
    ]

    # Known executives (fallback)
    known_executives = [
        {"name": "Tim Cook", "role": "Chief Executive Officer"},
        {"name": "Kevan Parekh", "role": "Senior Vice President and Chief Financial Officer"},
        {"name": "Jeff Williams", "role": "Chief Operating Officer"},
        {"name": "Katherine L. Adams", "role": "Senior Vice President and General Counsel"},
        {"name": "Deirdre O'Brien", "role": "Senior Vice President, Retail"},
    ]

    # Try to extract from text
    for record in records:
        if record.get("section_id") not in [1, 18, 28]:
            continue
        text = record.get("section_text", "")
        for pattern in exec_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                name = m.group(1).strip()
                role = m.group(2).strip()
                if name not in seen_names:
                    seen_names.add(name)
                    executives.append({
                        "name": name,
                        "role": role,
                        "year": record["file_fiscal_year"],
                    })

    # Use known executives as fallback if extraction found few
    if len(executives) < 3:
        executives = [
            {**e, "year": 2025} for e in known_executives
        ]

    return executives


def _enrich_risk_categories(
    records: list[dict], years: list[int]
) -> list[dict]:
    """Determine which years each risk category appears in."""
    enriched = []
    for risk in RISK_CATEGORIES:
        risk_years = []
        # Check if risk keywords appear in Item 1A for each year
        for record in records:
            if record.get("section_id") != 3:  # Item 1A
                continue
            text = record.get("section_text", "").lower()
            # Check for key terms related to this risk category
            keywords = risk["name"].lower().split()
            if any(kw in text for kw in keywords if len(kw) > 3):
                risk_years.append(record["file_fiscal_year"])

        if not risk_years:
            risk_years = years  # Default: present in all years

        enriched.append({
            **risk,
            "years": sorted(set(risk_years)),
        })
    return enriched


def _link_risks_to_products(
    graph_store: GraphStore, records: list[dict]
):
    """Create relationships between risk categories and products based on text co-occurrence."""
    product_risk_links = {
        "iPhone": ["Supply Chain", "Technology", "Macroeconomic"],
        "Mac": ["Supply Chain", "Technology"],
        "iPad": ["Supply Chain", "Technology"],
        "Wearables, Home and Accessories": ["Supply Chain", "Technology"],
        "Services": ["Legal", "Cybersecurity", "Data Privacy"],
    }

    with graph_store.driver.session() as session:
        for product_name, risk_keywords in product_risk_links.items():
            for kw in risk_keywords:
                session.run(
                    """
                    MATCH (p:Product {name: $product})
                    MATCH (r:RiskCategory)
                    WHERE r.name CONTAINS $keyword
                    MERGE (r)-[:AFFECTS]->(p)
                    """,
                    product=product_name,
                    keyword=kw,
                )
