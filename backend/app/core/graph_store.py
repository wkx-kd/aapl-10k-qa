"""Neo4j graph store for knowledge graph operations."""

import logging
from typing import Optional

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class GraphStore:
    """Manages Neo4j knowledge graph for entity relationship queries."""

    def __init__(
        self,
        uri: str = "bolt://neo4j:7687",
        user: str = "neo4j",
        password: str = "neo4jpassword",
    ):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
        return self._driver

    def verify_connection(self):
        """Test the connection to Neo4j."""
        self.driver.verify_connectivity()
        logger.info(f"Connected to Neo4j at {self.uri}")

    def clear_graph(self):
        """Delete all nodes and relationships."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("Cleared all graph data")

    def create_constraints(self):
        """Create uniqueness constraints for entity types."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Segment) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Executive) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (y:FiscalYear) REQUIRE y.year IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:RiskCategory) REQUIRE r.name IS UNIQUE",
        ]
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.warning(f"Constraint creation warning: {e}")
        logger.info("Graph constraints created")

    def build_company_node(self):
        """Create the Apple Inc. company node."""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (c:Company {name: 'Apple Inc.'})
                SET c.ticker = 'AAPL',
                    c.industry = 'Technology',
                    c.description = 'Designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories'
                """
            )

    def build_fiscal_years(self, years: list[int]):
        """Create fiscal year nodes."""
        with self.driver.session() as session:
            for year in years:
                session.run(
                    "MERGE (y:FiscalYear {year: $year})",
                    year=year,
                )

    def build_products(self, products: list[dict]):
        """Create product nodes and link to company.

        products: [{"name": "iPhone", "category": "Hardware", "description": "..."}]
        """
        with self.driver.session() as session:
            for prod in products:
                session.run(
                    """
                    MERGE (p:Product {name: $name})
                    SET p.category = $category, p.description = $description
                    WITH p
                    MATCH (c:Company {name: 'Apple Inc.'})
                    MERGE (c)-[:HAS_PRODUCT]->(p)
                    """,
                    name=prod["name"],
                    category=prod.get("category", ""),
                    description=prod.get("description", ""),
                )

    def build_segments(self, segments: list[dict]):
        """Create geographic segment nodes.

        segments: [{"name": "Americas", "description": "..."}]
        """
        with self.driver.session() as session:
            for seg in segments:
                session.run(
                    """
                    MERGE (s:Segment {name: $name})
                    SET s.description = $description
                    WITH s
                    MATCH (c:Company {name: 'Apple Inc.'})
                    MERGE (c)-[:OPERATES_IN]->(s)
                    """,
                    name=seg["name"],
                    description=seg.get("description", ""),
                )

    def build_executives(self, executives: list[dict]):
        """Create executive nodes.

        executives: [{"name": "Tim Cook", "role": "CEO", "year": 2025}]
        """
        with self.driver.session() as session:
            for exec in executives:
                session.run(
                    """
                    MERGE (e:Executive {name: $name})
                    SET e.role = $role
                    WITH e
                    MATCH (c:Company {name: 'Apple Inc.'})
                    MERGE (c)-[:LED_BY {role: $role, since_year: $year}]->(e)
                    """,
                    name=exec["name"],
                    role=exec.get("role", ""),
                    year=exec.get("year", 2025),
                )

    def build_risk_categories(self, risks: list[dict]):
        """Create risk category nodes.

        risks: [{"name": "Supply Chain Risk", "description": "...", "years": [2020, 2025]}]
        """
        with self.driver.session() as session:
            for risk in risks:
                session.run(
                    """
                    MERGE (r:RiskCategory {name: $name})
                    SET r.description = $description
                    WITH r
                    MATCH (c:Company {name: 'Apple Inc.'})
                    MERGE (c)-[:FACES_RISK]->(r)
                    """,
                    name=risk["name"],
                    description=risk.get("description", ""),
                )
                # Link to fiscal years
                for year in risk.get("years", []):
                    session.run(
                        """
                        MATCH (r:RiskCategory {name: $name})
                        MATCH (y:FiscalYear {year: $year})
                        MERGE (r)-[:REPORTED_IN]->(y)
                        """,
                        name=risk["name"],
                        year=year,
                    )

    def build_financial_links(self, metrics: dict[int, dict]):
        """Link financial metrics to fiscal years and products."""
        with self.driver.session() as session:
            for year, data in metrics.items():
                inc = data.get("income_statement", {})
                if inc.get("revenue"):
                    session.run(
                        """
                        MATCH (c:Company {name: 'Apple Inc.'})
                        MATCH (y:FiscalYear {year: $year})
                        MERGE (c)-[r:REPORTED_REVENUE]->(y)
                        SET r.amount = $revenue,
                            r.net_income = $net_income,
                            r.operating_income = $operating_income
                        """,
                        year=year,
                        revenue=inc.get("revenue"),
                        net_income=inc.get("net_income"),
                        operating_income=inc.get("operating_income"),
                    )

    def execute_cypher(self, cypher: str) -> list[dict]:
        """Execute a read-only Cypher query with safety checks."""
        cleaned = cypher.strip().rstrip(";")

        # Security: block write operations
        write_keywords = [
            "CREATE", "MERGE", "DELETE", "DETACH", "SET", "REMOVE",
            "DROP", "CALL", "LOAD",
        ]
        upper = cleaned.upper()
        for kw in write_keywords:
            if kw in upper and "MATCH" not in upper.split(kw)[0]:
                # Allow MATCH...RETURN but not standalone write ops
                if not upper.startswith("MATCH"):
                    raise ValueError(
                        f"Write operation '{kw}' not allowed in read-only queries"
                    )

        try:
            with self.driver.session() as session:
                result = session.run(cleaned)
                records = []
                for record in result:
                    records.append(dict(record))
                return records
        except Exception as e:
            logger.error(f"Cypher execution error: {e}")
            raise ValueError(f"Cypher execution error: {e}")

    def get_all_entities(self) -> dict:
        """Get summary of all entities in the graph."""
        with self.driver.session() as session:
            result = {}

            # Count by label
            counts = session.run(
                "CALL db.labels() YIELD label "
                "CALL { WITH label MATCH (n) WHERE label IN labels(n) RETURN count(n) AS cnt } "
                "RETURN label, cnt"
            )
            result["entity_counts"] = {
                r["label"]: r["cnt"] for r in counts
            }

            # Get products
            products = session.run(
                "MATCH (c:Company)-[:HAS_PRODUCT]->(p:Product) RETURN p.name AS name, p.category AS category"
            )
            result["products"] = [dict(r) for r in products]

            # Get segments
            segments = session.run(
                "MATCH (c:Company)-[:OPERATES_IN]->(s:Segment) RETURN s.name AS name"
            )
            result["segments"] = [dict(r) for r in segments]

            # Get risk categories
            risks = session.run(
                "MATCH (c:Company)-[:FACES_RISK]->(r:RiskCategory) RETURN r.name AS name, r.description AS description"
            )
            result["risk_categories"] = [dict(r) for r in risks]

            # Get executives
            execs = session.run(
                "MATCH (c:Company)-[rel:LED_BY]->(e:Executive) RETURN e.name AS name, rel.role AS role"
            )
            result["executives"] = [dict(r) for r in execs]

            return result

    def get_schema_description(self) -> str:
        """Get graph schema description for LLM Cypher generation."""
        return """Neo4j Knowledge Graph Schema:

Node Labels:
- Company: {name, ticker, industry, description}
- Product: {name, category, description}
- Segment: {name, description}
- Executive: {name, role}
- FiscalYear: {year}
- RiskCategory: {name, description}

Relationships:
- (Company)-[:HAS_PRODUCT]->(Product)
- (Company)-[:OPERATES_IN]->(Segment)
- (Company)-[:FACES_RISK]->(RiskCategory)
- (Company)-[:LED_BY {role, since_year}]->(Executive)
- (Company)-[:REPORTED_REVENUE {amount, net_income, operating_income}]->(FiscalYear)
- (RiskCategory)-[:REPORTED_IN]->(FiscalYear)

Notes:
- There is only one Company node: Apple Inc. (ticker: AAPL)
- Products include: iPhone, Mac, iPad, Wearables/Home/Accessories, Services
- Segments: Americas, Europe, Greater China, Japan, Rest of Asia Pacific
- FiscalYear nodes cover 2020-2025"""

    def has_data(self) -> bool:
        """Check if the graph has been populated."""
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) AS cnt")
                count = result.single()["cnt"]
                return count > 0
        except Exception:
            return False

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
