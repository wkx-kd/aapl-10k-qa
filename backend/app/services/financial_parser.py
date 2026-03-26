"""Parse structured financial tables from 10-K sections 25, 26, 27."""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_financial_table(text: str) -> dict:
    """Parse a structured financial table into a dict of {date: {label: value}}.

    The tables have format:
        Header line (e.g., "Balance Sheet for 320193 as of 2025-10-31:")
        Column headers: label  date1  date2  [date3]
        Data rows: label  value1  value2  [value3]
    """
    lines = text.strip().split("\n")
    if not lines:
        return {}

    # Extract column dates from header area
    dates = []
    data_start_idx = 0

    for i, line in enumerate(lines):
        # Look for date patterns in header lines
        found_dates = re.findall(r"\d{4}-\d{2}-\d{2}", line)
        if found_dates and not dates:
            dates = found_dates
            data_start_idx = i + 1
            break

    if not dates:
        logger.warning("Could not find date headers in financial table")
        return {}

    # Extract fiscal years from dates
    years = [int(d.split("-")[0]) for d in dates]

    # Parse data rows
    result = {year: {} for year in years}

    for line in lines[data_start_idx:]:
        if not line.strip():
            continue

        # Extract numeric values from the line
        # Values look like: 35934000000.0 or -220960000000.0 or just a number like 7.49
        values = re.findall(r"-?[\d]+(?:\.[\d]+)?", line)

        if not values:
            continue

        # The label is the text before the first number
        # Find position of the first number in the line
        first_num_match = re.search(r"\s+-?[\d]+(?:\.[\d]+)?\s*", line)
        if not first_num_match:
            continue

        label = line[: first_num_match.start()].strip()
        if not label:
            continue

        # Skip category headers (lines with only a label, no values that match column count)
        # We need values count to match or be close to dates count
        parsed_values = []
        for v in values:
            try:
                parsed_values.append(float(v))
            except ValueError:
                continue

        # Only keep rows where we have values matching column count
        if len(parsed_values) < len(years):
            continue

        # Map values to years (take last N values matching year count)
        mapped_values = parsed_values[: len(years)]

        for year, value in zip(years, mapped_values):
            result[year][label] = value

    return result


def extract_financial_metrics(records: list[dict]) -> dict[int, dict]:
    """Extract structured financial metrics from all years.

    Returns: {year: {income_statement: {...}, balance_sheet: {...}, cash_flow: {...}, derived: {...}}}
    """
    # Collect raw data from all financial table sections
    raw_data: dict[int, dict[str, dict]] = {}  # {year: {statement_type: {label: value}}}

    statement_types = {
        25: "balance_sheet",
        26: "income_statement",
        27: "cash_flow",
    }

    for record in records:
        sid = record.get("section_id")
        if sid not in statement_types:
            continue

        stmt_type = statement_types[sid]
        text = record.get("section_text", "")
        parsed = parse_financial_table(text)

        for year, metrics in parsed.items():
            if year not in raw_data:
                raw_data[year] = {}
            # Later filings may have restated figures - prefer most recent filing
            filing_year = record.get("file_fiscal_year", 0)
            key = f"{stmt_type}_filing_{filing_year}"

            if stmt_type not in raw_data[year] or filing_year >= raw_data[year].get(
                f"_{stmt_type}_source_year", 0
            ):
                raw_data[year][stmt_type] = metrics
                raw_data[year][f"_{stmt_type}_source_year"] = filing_year

    # Normalize into standardized metrics
    all_metrics = {}
    for year, data in sorted(raw_data.items()):
        metrics = {
            "year": year,
            "income_statement": _normalize_income_statement(
                data.get("income_statement", {})
            ),
            "balance_sheet": _normalize_balance_sheet(
                data.get("balance_sheet", {})
            ),
            "cash_flow": _normalize_cash_flow(data.get("cash_flow", {})),
        }
        metrics["derived"] = _compute_derived_metrics(metrics)
        all_metrics[year] = metrics

    logger.info(f"Extracted financial metrics for years: {sorted(all_metrics.keys())}")
    return all_metrics


def _find_metric(data: dict, *possible_labels: str) -> Optional[float]:
    """Find a metric value by trying multiple possible labels."""
    for label in possible_labels:
        for key, value in data.items():
            if label.lower() in key.lower():
                return value
    return None


def _normalize_income_statement(data: dict) -> dict:
    """Map raw income statement labels to standardized names."""
    return {
        "revenue": _find_metric(data, "Revenue"),
        "cost_of_revenue": _find_metric(data, "Cost of Revenue"),
        "gross_profit": _find_metric(data, "Gross Profit"),
        "rd_expense": _find_metric(data, "Research and Development"),
        "sga_expense": _find_metric(
            data, "Selling, General and Administrative"
        ),
        "operating_expenses": _find_metric(data, "Operating Expenses"),
        "operating_income": _find_metric(data, "Operating Income"),
        "net_income": _find_metric(data, "Net Income"),
        "eps_basic": _find_metric(data, "Earnings Per Share"),
        "eps_diluted": _find_metric(data, "Earnings Per Share (Diluted)"),
        "shares_outstanding": _find_metric(data, "Shares Outstanding"),
    }


def _normalize_balance_sheet(data: dict) -> dict:
    """Map raw balance sheet labels to standardized names."""
    return {
        "cash_and_equivalents": _find_metric(
            data, "Cash and Cash Equivalents"
        ),
        "marketable_securities_current": _find_metric(
            data, "Marketable Securities"
        ),
        "accounts_receivable": _find_metric(data, "Accounts Receivable"),
        "inventory": _find_metric(data, "Inventory"),
        "total_current_assets": _find_metric(data, "Total Current Assets"),
        "total_assets": _find_metric(data, "Total Assets"),
        "accounts_payable": _find_metric(data, "Accounts Payable"),
        "total_current_liabilities": _find_metric(
            data, "Total Current Liabilities"
        ),
        "long_term_debt": _find_metric(data, "Long-Term Debt"),
        "total_liabilities": _find_metric(data, "Total Liabilities"),
        "stockholders_equity": _find_metric(
            data, "Stockholders", "Shareholders"
        ),
    }


def _normalize_cash_flow(data: dict) -> dict:
    """Map raw cash flow labels to standardized names."""
    return {
        "operating_cf": _find_metric(
            data, "Cash Generated by Operating Activities", "operating activities"
        ),
        "investing_cf": _find_metric(
            data, "Cash Generated by Investing Activities", "investing activities"
        ),
        "financing_cf": _find_metric(
            data, "Cash Used in Financing Activities", "financing activities"
        ),
        "capex": _find_metric(
            data, "capital expenditure", "Payments for Acquisition of Property"
        ),
        "dividends_paid": _find_metric(data, "Dividends", "dividends paid"),
        "stock_repurchases": _find_metric(
            data, "Repurchases of Common Stock", "stock repurchase"
        ),
        "depreciation": _find_metric(data, "Depreciation and amortization"),
        "stock_based_comp": _find_metric(data, "Share-based compensation"),
    }


def _compute_derived_metrics(metrics: dict) -> dict:
    """Compute derived financial ratios."""
    inc = metrics.get("income_statement", {})
    bs = metrics.get("balance_sheet", {})
    cf = metrics.get("cash_flow", {})

    revenue = inc.get("revenue")
    gross_profit = inc.get("gross_profit")
    operating_income = inc.get("operating_income")
    net_income = inc.get("net_income")

    total_current_assets = bs.get("total_current_assets")
    total_current_liabilities = bs.get("total_current_liabilities")
    total_liabilities = bs.get("total_liabilities")
    stockholders_equity = bs.get("stockholders_equity")

    operating_cf = cf.get("operating_cf")
    capex = cf.get("capex")

    derived = {}

    # Margins
    if revenue and revenue != 0:
        if gross_profit is not None:
            derived["gross_margin"] = round(gross_profit / revenue, 4)
        if operating_income is not None:
            derived["operating_margin"] = round(operating_income / revenue, 4)
        if net_income is not None:
            derived["net_margin"] = round(net_income / revenue, 4)

    # Liquidity
    if total_current_assets and total_current_liabilities and total_current_liabilities != 0:
        derived["current_ratio"] = round(
            total_current_assets / total_current_liabilities, 4
        )

    # Leverage
    if total_liabilities and stockholders_equity and stockholders_equity != 0:
        derived["debt_to_equity"] = round(
            total_liabilities / stockholders_equity, 4
        )

    # Free Cash Flow
    if operating_cf is not None and capex is not None:
        derived["free_cash_flow"] = operating_cf + capex  # capex is negative

    return derived
