"""Financial data API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Request, Query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/financial/metrics")
async def get_metrics(
    request: Request,
    years: Optional[str] = Query(None, description="Comma-separated years, e.g., '2024,2025'"),
):
    """Get all financial metrics, optionally filtered by years."""
    sql_store = request.app.state.sql_store

    year_list = None
    if years:
        year_list = [int(y.strip()) for y in years.split(",")]

    metrics = sql_store.get_all_metrics(years=year_list)
    return {"metrics": metrics}


@router.get("/financial/compare")
async def compare_metrics(
    request: Request,
    metric: str = Query(..., description="Metric name, e.g., 'revenue', 'net_income'"),
    years: Optional[str] = Query(None, description="Comma-separated years"),
):
    """Compare a specific metric across years."""
    sql_store = request.app.state.sql_store

    # Map metric to table and column
    metric_map = {
        "revenue": ("income_statement", "revenue"),
        "gross_profit": ("income_statement", "gross_profit"),
        "operating_income": ("income_statement", "operating_income"),
        "net_income": ("income_statement", "net_income"),
        "eps_basic": ("income_statement", "eps_basic"),
        "eps_diluted": ("income_statement", "eps_diluted"),
        "total_assets": ("balance_sheet", "total_assets"),
        "total_liabilities": ("balance_sheet", "total_liabilities"),
        "stockholders_equity": ("balance_sheet", "stockholders_equity"),
        "cash_and_equivalents": ("balance_sheet", "cash_and_equivalents"),
        "operating_cf": ("cash_flow", "operating_cf"),
        "free_cash_flow": ("derived_metrics", "free_cash_flow"),
        "gross_margin": ("derived_metrics", "gross_margin"),
        "operating_margin": ("derived_metrics", "operating_margin"),
        "net_margin": ("derived_metrics", "net_margin"),
        "current_ratio": ("derived_metrics", "current_ratio"),
        "debt_to_equity": ("derived_metrics", "debt_to_equity"),
        "revenue_yoy_growth": ("derived_metrics", "revenue_yoy_growth"),
    }

    if metric not in metric_map:
        return {"error": f"Unknown metric: {metric}", "available": list(metric_map.keys())}

    table, column = metric_map[metric]
    where = ""
    if years:
        year_list = [y.strip() for y in years.split(",")]
        where = f"WHERE year IN ({','.join(year_list)})"

    sql = f"SELECT year, {column} FROM {table} {where} ORDER BY year"
    results = sql_store.execute_safe_query(sql)

    return {
        "metric": metric,
        "data": results,
    }


@router.get("/financial/summary")
async def get_summary(request: Request):
    """Get key financial summary for all years."""
    sql_store = request.app.state.sql_store

    sql = """
    SELECT
        i.year,
        i.revenue,
        i.net_income,
        i.eps_diluted,
        d.gross_margin,
        d.operating_margin,
        d.net_margin,
        d.free_cash_flow,
        d.revenue_yoy_growth,
        b.total_assets,
        b.cash_and_equivalents,
        d.current_ratio,
        d.debt_to_equity
    FROM income_statement i
    JOIN derived_metrics d ON i.year = d.year
    JOIN balance_sheet b ON i.year = b.year
    ORDER BY i.year
    """

    results = sql_store.execute_safe_query(sql)
    return {"summary": results}
