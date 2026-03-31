"""
Flight and backlog analysis tools.

This module provides analysis tools for answering questions
about flight and backlog data with filtering and aggregation capabilities.

AUTOMATIC FILTER CONTEXT:
- These tools automatically read the active filter from the ContextVar
  set by filter tools. The LLM does NOT need to pass filter parameters.
- Just call analyze_flights(question="...") or analyze_backlog(question="...")
  and it will analyze whatever is currently displayed on the dashboard.
"""

from __future__ import annotations

import logging
from typing import Annotated

from agent_framework import tool
from pydantic import Field

from ..utils import _get_all_backlog_jobs, _get_all_flights, current_active_filter

logger = logging.getLogger(__name__)


@tool(
    name="analyze_flights",
    description="""Answer questions about the flights currently displayed on the dashboard.

This tool analyzes the current data WITHOUT changing the dashboard display.
NEVER call filter_flights before this - just use analyze_flights directly.

Optional filter parameters let you analyze subsets:
- analyze_utilization: Count/analyze flights with specific status ("optimal", "over", "under", "near_capacity")
- analyze_route_from/to: Analyze specific route
- analyze_risk: Analyze by risk level

These filters are for ANALYSIS ONLY - they do not change the dashboard view.
""",
)
def analyze_flights(
    question: Annotated[
        str,
        Field(description="The user's question about the currently displayed flights"),
    ] = "general summary",
    analyze_utilization: Annotated[
        str | None,
        Field(
            description="Optional: Filter analysis to specific utilization status ('optimal', 'over', 'under', 'near_capacity')"
        ),
    ] = None,
    analyze_route_from: Annotated[
        str | None,
        Field(description="Optional: Filter analysis to flights from this airport code"),
    ] = None,
    analyze_route_to: Annotated[
        str | None,
        Field(description="Optional: Filter analysis to flights to this airport code"),
    ] = None,
    analyze_risk: Annotated[
        str | None,
        Field(
            description="Optional: Filter analysis to specific risk level ('critical', 'high', 'medium', 'low')"
        ),
    ] = None,
) -> dict:
    """
    Analyze flight data with optional subset filtering.

    This tool can use both:
    1. The current dashboard filter (from ContextVar)
    2. Additional analyze_* parameters for ad-hoc subset analysis

    The analyze_* parameters let the LLM ask questions about subsets
    (e.g., "how many optimal?") without changing the dashboard display.
    """
    # Read the current active filter from ContextVar (synced from frontend context)
    active_filter = current_active_filter.get()

    # Start with filter from ContextVar (what's displayed on dashboard)
    utilization_type = active_filter.get("utilizationType") if active_filter else None
    route_from = active_filter.get("routeFrom") if active_filter else None
    route_to = active_filter.get("routeTo") if active_filter else None
    risk_level = active_filter.get("riskLevel") if active_filter else None

    # Override with analyze_* parameters if provided (for subset analysis)
    # These let the LLM analyze subsets without changing the dashboard
    if analyze_utilization:
        utilization_type = analyze_utilization
    if analyze_route_from:
        route_from = analyze_route_from
    if analyze_route_to:
        route_to = analyze_route_to
    if analyze_risk:
        risk_level = analyze_risk

    # Log what we're analyzing
    logger.info(
        "[analyze_flights] Filters - context: %s, analyze_params: util=%s, route=%s->%s, risk=%s, question=%s",
        active_filter,
        analyze_utilization,
        analyze_route_from,
        analyze_route_to,
        analyze_risk,
        question,
    )
    logger.info(
        "[analyze_flights] Effective filter: util=%s, route=%s->%s, risk=%s",
        utilization_type,
        route_from,
        route_to,
        risk_level,
    )

    # Fetch ALL flights from MCP server
    all_flights = _get_all_flights()

    # Start with all flights
    flights = all_flights

    # Apply filters (from context + analyze_* overrides)
    if utilization_type == "over":
        flights = [f for f in flights if f.get("utilizationPercent", 0) > 95]
    elif utilization_type == "near_capacity":
        flights = [f for f in flights if 85 <= f.get("utilizationPercent", 0) <= 95]
    elif utilization_type == "optimal":
        flights = [f for f in flights if 50 <= f.get("utilizationPercent", 0) < 85]
    elif utilization_type == "under":
        flights = [f for f in flights if f.get("utilizationPercent", 0) < 50]

    # Apply route filters
    if route_from:
        flights = [f for f in flights if f.get("from", "").upper() == route_from.upper()]
    if route_to:
        flights = [f for f in flights if f.get("to", "").upper() == route_to.upper()]

    # Apply risk level filter
    if risk_level:
        flights = [f for f in flights if f.get("riskLevel") == risk_level.lower()]

    # Build filter description for logging/response
    filter_parts = []
    if route_from:
        filter_parts.append(f"from {route_from}")
    if route_to:
        filter_parts.append(f"to {route_to}")
    if utilization_type:
        filter_parts.append(f"{utilization_type} utilization")
    if risk_level:
        filter_parts.append(f"{risk_level} risk")

    filter_str = " with ".join(filter_parts) if filter_parts else "all flights"
    logger.info("[analyze_flights] Analyzing %d flights (%s)", len(flights), filter_str)

    if not flights:
        return {
            "message": f"No flights found matching the criteria ({filter_str}).",
            "flight_count": 0,
            "filter_applied": filter_str,
        }

    # Calculate stats
    total = len(flights)
    avg_util = sum(f.get("utilizationPercent", 0) for f in flights) / total

    # Risk breakdown
    critical = len([f for f in flights if f.get("riskLevel") == "critical"])
    high = len([f for f in flights if f.get("riskLevel") == "high"])
    medium = len([f for f in flights if f.get("riskLevel") == "medium"])
    low = len([f for f in flights if f.get("riskLevel") == "low"])

    # Route breakdown
    route_counts: dict[str, int] = {}
    for f in flights:
        route = f"{f.get('from')} → {f.get('to')}"
        route_counts[route] = route_counts.get(route, 0) + 1

    routes_sorted = sorted(route_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "message": f"Analyzed {total} flights" + (f" ({filter_str})" if filter_parts else ""),
        "flight_count": total,
        "filter_applied": filter_str if filter_parts else "none (all flights)",
        "average_utilization": round(avg_util, 1),
        "risk_breakdown": {
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        },
        "route_breakdown": dict(routes_sorted[:5]),
        "question": question,
    }


# ============================================================================
# Backlog Analysis Tool
# ============================================================================


@tool(
    name="analyze_backlog",
    description="""Answer questions about the workable backlog jobs currently displayed on the dashboard.

This tool analyzes the current backlog data WITHOUT changing the dashboard display.
NEVER call filter_jobs before this - just use analyze_backlog directly.

Optional filter parameters let you analyze subsets:
- analyze_job_type: Filter by job type ("Fixed Price" or "T&M")
- analyze_ready_to_work: Filter by readiness (true/false)
- analyze_customer: Filter by customer name (partial match)
- analyze_labor_type: Filter by labor type ("Crew" or "Single Mechanic")
- analyze_bill_month: Filter by final billing month ("Mar", "Apr", "May", "Jun", "Jul")

These filters are for ANALYSIS ONLY - they do not change the dashboard view.
""",
)
def analyze_backlog(
    question: Annotated[
        str,
        Field(description="The user's question about the workable backlog"),
    ] = "general summary",
    analyze_job_type: Annotated[
        str | None,
        Field(description="Optional: Filter analysis to job type ('Fixed Price' or 'T&M')"),
    ] = None,
    analyze_ready_to_work: Annotated[
        bool | None,
        Field(description="Optional: Filter analysis to ready (true) or not ready (false) jobs"),
    ] = None,
    analyze_customer: Annotated[
        str | None,
        Field(description="Optional: Filter analysis to jobs for this customer (partial match)"),
    ] = None,
    analyze_labor_type: Annotated[
        str | None,
        Field(description="Optional: Filter analysis to labor type ('Crew' or 'Single Mechanic')"),
    ] = None,
    analyze_bill_month: Annotated[
        str | None,
        Field(
            description="Optional: Filter analysis to billing month ('Mar', 'Apr', 'May', 'Jun', 'Jul')"
        ),
    ] = None,
) -> dict:
    """
    Analyze workable backlog data with optional subset filtering.

    This tool can use both:
    1. The current dashboard filter (from ContextVar)
    2. Additional analyze_* parameters for ad-hoc subset analysis

    The analyze_* parameters let the LLM ask questions about subsets
    without changing the dashboard display.
    """
    # Read the current active filter from ContextVar (synced from frontend context)
    active_filter = current_active_filter.get()

    # Start with filter from ContextVar (what's displayed on dashboard)
    job_type = active_filter.get("jobType") if active_filter else None
    ready_to_work = active_filter.get("readyToWork") if active_filter else None
    customer_name = active_filter.get("customerName") if active_filter else None
    labor_type = active_filter.get("laborType") if active_filter else None
    bill_month = active_filter.get("finalBillMonth") if active_filter else None

    # Override with analyze_* parameters if provided (for subset analysis)
    if analyze_job_type:
        job_type = analyze_job_type
    if analyze_ready_to_work is not None:
        ready_to_work = analyze_ready_to_work
    if analyze_customer:
        customer_name = analyze_customer
    if analyze_labor_type:
        labor_type = analyze_labor_type
    if analyze_bill_month:
        bill_month = analyze_bill_month

    # Log what we're analyzing
    logger.info(
        "[analyze_backlog] Filters - context: %s, analyze_params: job_type=%s, ready=%s, customer=%s, labor=%s, month=%s, question=%s",
        active_filter,
        analyze_job_type,
        analyze_ready_to_work,
        analyze_customer,
        analyze_labor_type,
        analyze_bill_month,
        question,
    )

    # Fetch ALL backlog jobs from MCP server
    all_jobs = _get_all_backlog_jobs()

    # Start with all jobs
    jobs = all_jobs

    # Apply filters (from context + analyze_* overrides)
    if job_type:
        jobs = [j for j in jobs if j.get("jobType", "").lower() == job_type.lower()]

    if ready_to_work is not None:
        jobs = [j for j in jobs if j.get("readyToWork") == ready_to_work]

    if customer_name:
        customer_lower = customer_name.lower()
        jobs = [j for j in jobs if customer_lower in j.get("customerName", "").lower()]

    if labor_type:
        jobs = [j for j in jobs if j.get("laborType", "").lower() == labor_type.lower()]

    if bill_month:
        jobs = [j for j in jobs if j.get("finalBillMonth", "").lower() == bill_month.lower()]

    # Build filter description for logging/response
    filter_parts = []
    if job_type:
        filter_parts.append(f"{job_type} jobs")
    if ready_to_work is not None:
        filter_parts.append("ready to work" if ready_to_work else "not ready")
    if customer_name:
        filter_parts.append(f"customer: {customer_name}")
    if labor_type:
        filter_parts.append(f"{labor_type}")
    if bill_month:
        filter_parts.append(f"billing in {bill_month}")

    filter_str = " with ".join(filter_parts) if filter_parts else "all jobs"
    logger.info("[analyze_backlog] Analyzing %d jobs (%s)", len(jobs), filter_str)

    if not jobs:
        return {
            "message": f"No jobs found matching the criteria ({filter_str}).",
            "job_count": 0,
            "filter_applied": filter_str,
        }

    # Calculate stats
    total = len(jobs)
    total_selling = sum(j.get("sellingAmount", 0) for j in jobs)
    total_workable = sum(j.get("workableBacklogAmount", 0) for j in jobs)
    total_margin = sum(j.get("projectedMargin", 0) for j in jobs)
    avg_job_value = total_selling / total if total > 0 else 0

    # Ready to work breakdown
    ready_count = len([j for j in jobs if j.get("readyToWork")])
    not_ready_count = total - ready_count

    # Job type breakdown
    fixed_price = len([j for j in jobs if j.get("jobType") == "Fixed Price"])
    t_and_m = len([j for j in jobs if j.get("jobType") == "T&M"])

    # Labor type breakdown
    crew_jobs = len([j for j in jobs if j.get("laborType") == "Crew"])
    mechanic_jobs = len([j for j in jobs if j.get("laborType") == "Single Mechanic"])

    # Revenue by month
    month_revenue: dict[str, float] = {}
    for j in jobs:
        month = j.get("finalBillMonth", "Unknown")
        month_revenue[month] = month_revenue.get(month, 0) + j.get("sellingAmount", 0)

    # Top customers by value
    customer_value: dict[str, float] = {}
    for j in jobs:
        cust = j.get("customerName", "Unknown")
        customer_value[cust] = customer_value.get(cust, 0) + j.get("sellingAmount", 0)
    top_customers = dict(sorted(customer_value.items(), key=lambda x: x[1], reverse=True)[:5])

    return {
        "message": f"Analyzed {total} jobs" + (f" ({filter_str})" if filter_parts else ""),
        "job_count": total,
        "filter_applied": filter_str if filter_parts else "none (all jobs)",
        "total_selling_amount": round(total_selling, 2),
        "total_workable_backlog": round(total_workable, 2),
        "total_projected_margin": round(total_margin, 2),
        "average_job_value": round(avg_job_value, 2),
        "readiness_breakdown": {
            "ready_to_work": ready_count,
            "not_ready": not_ready_count,
        },
        "job_type_breakdown": {
            "Fixed Price": fixed_price,
            "T&M": t_and_m,
        },
        "labor_type_breakdown": {
            "Crew": crew_jobs,
            "Single Mechanic": mechanic_jobs,
        },
        "revenue_by_month": {k: round(v, 2) for k, v in month_revenue.items()},
        "top_customers_by_value": {k: round(v, 2) for k, v in top_customers.items()},
        "question": question,
    }
