"""SQLite store for structured financial data with Text-to-SQL support."""

import sqlite3
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SQLStore:
    """Manages SQLite database for structured financial metrics."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def init_tables(self):
        """Create financial data tables."""
        cursor = self.conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS income_statement (
                year INTEGER PRIMARY KEY,
                revenue REAL,
                cost_of_revenue REAL,
                gross_profit REAL,
                rd_expense REAL,
                sga_expense REAL,
                operating_expenses REAL,
                operating_income REAL,
                net_income REAL,
                eps_basic REAL,
                eps_diluted REAL,
                shares_outstanding REAL
            );

            CREATE TABLE IF NOT EXISTS balance_sheet (
                year INTEGER PRIMARY KEY,
                cash_and_equivalents REAL,
                marketable_securities_current REAL,
                accounts_receivable REAL,
                inventory REAL,
                total_current_assets REAL,
                total_assets REAL,
                accounts_payable REAL,
                total_current_liabilities REAL,
                long_term_debt REAL,
                total_liabilities REAL,
                stockholders_equity REAL
            );

            CREATE TABLE IF NOT EXISTS cash_flow (
                year INTEGER PRIMARY KEY,
                operating_cf REAL,
                investing_cf REAL,
                financing_cf REAL,
                capex REAL,
                dividends_paid REAL,
                stock_repurchases REAL,
                depreciation REAL,
                stock_based_comp REAL
            );

            CREATE TABLE IF NOT EXISTS derived_metrics (
                year INTEGER PRIMARY KEY,
                gross_margin REAL,
                operating_margin REAL,
                net_margin REAL,
                current_ratio REAL,
                debt_to_equity REAL,
                free_cash_flow REAL,
                revenue_yoy_growth REAL
            );
        """)
        self.conn.commit()
        logger.info("SQLite tables initialized")

    def insert_metrics(self, all_metrics: dict[int, dict]):
        """Insert extracted financial metrics into SQLite tables."""
        cursor = self.conn.cursor()

        for year, metrics in sorted(all_metrics.items()):
            # Income Statement
            inc = metrics.get("income_statement", {})
            cursor.execute(
                """INSERT OR REPLACE INTO income_statement
                   (year, revenue, cost_of_revenue, gross_profit, rd_expense,
                    sga_expense, operating_expenses, operating_income, net_income,
                    eps_basic, eps_diluted, shares_outstanding)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    year,
                    inc.get("revenue"),
                    inc.get("cost_of_revenue"),
                    inc.get("gross_profit"),
                    inc.get("rd_expense"),
                    inc.get("sga_expense"),
                    inc.get("operating_expenses"),
                    inc.get("operating_income"),
                    inc.get("net_income"),
                    inc.get("eps_basic"),
                    inc.get("eps_diluted"),
                    inc.get("shares_outstanding"),
                ),
            )

            # Balance Sheet
            bs = metrics.get("balance_sheet", {})
            cursor.execute(
                """INSERT OR REPLACE INTO balance_sheet
                   (year, cash_and_equivalents, marketable_securities_current,
                    accounts_receivable, inventory, total_current_assets,
                    total_assets, accounts_payable, total_current_liabilities,
                    long_term_debt, total_liabilities, stockholders_equity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    year,
                    bs.get("cash_and_equivalents"),
                    bs.get("marketable_securities_current"),
                    bs.get("accounts_receivable"),
                    bs.get("inventory"),
                    bs.get("total_current_assets"),
                    bs.get("total_assets"),
                    bs.get("accounts_payable"),
                    bs.get("total_current_liabilities"),
                    bs.get("long_term_debt"),
                    bs.get("total_liabilities"),
                    bs.get("stockholders_equity"),
                ),
            )

            # Cash Flow
            cf = metrics.get("cash_flow", {})
            cursor.execute(
                """INSERT OR REPLACE INTO cash_flow
                   (year, operating_cf, investing_cf, financing_cf, capex,
                    dividends_paid, stock_repurchases, depreciation, stock_based_comp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    year,
                    cf.get("operating_cf"),
                    cf.get("investing_cf"),
                    cf.get("financing_cf"),
                    cf.get("capex"),
                    cf.get("dividends_paid"),
                    cf.get("stock_repurchases"),
                    cf.get("depreciation"),
                    cf.get("stock_based_comp"),
                ),
            )

            # Derived Metrics
            derived = metrics.get("derived", {})
            cursor.execute(
                """INSERT OR REPLACE INTO derived_metrics
                   (year, gross_margin, operating_margin, net_margin,
                    current_ratio, debt_to_equity, free_cash_flow, revenue_yoy_growth)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    year,
                    derived.get("gross_margin"),
                    derived.get("operating_margin"),
                    derived.get("net_margin"),
                    derived.get("current_ratio"),
                    derived.get("debt_to_equity"),
                    derived.get("free_cash_flow"),
                    derived.get("revenue_yoy_growth"),
                ),
            )

        # Compute YoY revenue growth
        cursor.execute("""
            UPDATE derived_metrics SET revenue_yoy_growth = (
                SELECT (i1.revenue - i2.revenue) / ABS(i2.revenue)
                FROM income_statement i1
                JOIN income_statement i2 ON i2.year = derived_metrics.year - 1
                WHERE i1.year = derived_metrics.year
                AND i2.revenue IS NOT NULL AND i2.revenue != 0
            )
        """)

        self.conn.commit()
        logger.info(f"Inserted financial metrics for {len(all_metrics)} years")

    def execute_safe_query(self, sql: str) -> list[dict]:
        """Execute a read-only SQL query with safety checks."""
        # Security: only allow SELECT statements
        cleaned = sql.strip().rstrip(";").strip()
        if not cleaned.upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")

        # Block dangerous patterns
        dangerous = re.compile(
            r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|ATTACH|DETACH)\b",
            re.IGNORECASE,
        )
        if dangerous.search(cleaned):
            raise ValueError("Query contains disallowed operations")

        try:
            cursor = self.conn.cursor()
            cursor.execute(cleaned)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"SQL execution error: {e}")
            raise ValueError(f"SQL execution error: {e}")

    def get_all_metrics(self, years: Optional[list[int]] = None) -> dict:
        """Get all financial metrics, optionally filtered by years."""
        where = ""
        params: list = []
        if years:
            placeholders = ",".join("?" for _ in years)
            where = f"WHERE year IN ({placeholders})"
            params = list(years)

        result = {}
        for table in [
            "income_statement",
            "balance_sheet",
            "cash_flow",
            "derived_metrics",
        ]:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM {table} {where} ORDER BY year", params)
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                year = row_dict.pop("year")
                if year not in result:
                    result[year] = {"year": year}
                result[year][table] = row_dict

        return result

    def get_table_schema(self) -> str:
        """Get schema description for LLM prompt."""
        return """Available SQLite tables and columns:

1. income_statement: year (INTEGER), revenue (REAL), cost_of_revenue (REAL), gross_profit (REAL), rd_expense (REAL), sga_expense (REAL), operating_expenses (REAL), operating_income (REAL), net_income (REAL), eps_basic (REAL), eps_diluted (REAL), shares_outstanding (REAL)

2. balance_sheet: year (INTEGER), cash_and_equivalents (REAL), marketable_securities_current (REAL), accounts_receivable (REAL), inventory (REAL), total_current_assets (REAL), total_assets (REAL), accounts_payable (REAL), total_current_liabilities (REAL), long_term_debt (REAL), total_liabilities (REAL), stockholders_equity (REAL)

3. cash_flow: year (INTEGER), operating_cf (REAL), investing_cf (REAL), financing_cf (REAL), capex (REAL), dividends_paid (REAL), stock_repurchases (REAL), depreciation (REAL), stock_based_comp (REAL)

4. derived_metrics: year (INTEGER), gross_margin (REAL), operating_margin (REAL), net_margin (REAL), current_ratio (REAL), debt_to_equity (REAL), free_cash_flow (REAL), revenue_yoy_growth (REAL)

Notes:
- All monetary values are in USD (original values, e.g., revenue=416161000000 means $416.161 billion)
- Margins are decimal ratios (e.g., gross_margin=0.469 means 46.9%)
- Year range: 2020-2025
- Negative values in cost/expense fields indicate outflows"""

    def is_initialized(self) -> bool:
        """Check if the database has been populated."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM income_statement")
            count = cursor.fetchone()[0]
            return count > 0
        except sqlite3.Error:
            return False

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
