"""
Backlog dashboard filter tools.

These tools control the filter state in the backlog dashboard, allowing users
to filter jobs by customer, job type, labor type, readiness, and billing month.
"""

from __future__ import annotations

import logging
from typing import Annotated

from agent_framework import tool
from pydantic import Field

from ..utils import current_active_filter

logger = logging.getLogger(__name__)


@tool(
    name="filter_jobs",
    description="Filter jobs in the backlog dashboard. Filters are ALWAYS additive - new filters combine with existing ones. Use reset_job_filters to clear all filters first.",
)
def filter_jobs(
    customer_name: Annotated[
        str | None,
        Field(description="Filter by customer name (partial match, e.g., 'Borgata')"),
    ] = None,
    job_type: Annotated[
        str | None,
        Field(description="Job type: 'Fixed Price' or 'T&M'"),
    ] = None,
    labor_type: Annotated[
        str | None,
        Field(description="Labor type: 'Crew' or 'Single Mechanic'"),
    ] = None,
    ready_to_work: Annotated[
        bool | None,
        Field(description="Filter by readiness: true for ready jobs, false for not ready"),
    ] = None,
    final_bill_month: Annotated[
        str | None,
        Field(description="Filter by billing month: 'Mar', 'Apr', 'May', 'Jun', 'Jul'"),
    ] = None,
    min_selling_amount: Annotated[
        float | None,
        Field(description="Minimum selling amount filter (e.g., 50000 for jobs over $50k)"),
    ] = None,
    max_selling_amount: Annotated[
        float | None,
        Field(description="Maximum selling amount filter"),
    ] = None,
    limit: Annotated[
        int | None,
        Field(description="Max jobs to return (default 100, max 100)"),
    ] = None,
) -> dict:
    """Set the filter state for backlog jobs. Filters are ALWAYS additive."""
    max_limit = min(limit or 100, 100) if limit else 100

    # Get existing filter from ContextVar (synced from frontend context at request start)
    existing_filter = current_active_filter.get() or {}
    logger.info("[filter_jobs] Existing filter from context: %s", existing_filter)

    # ALWAYS ADDITIVE - merge new values with existing filter
    active_filter = {
        "customerName": customer_name if customer_name else existing_filter.get("customerName"),
        "jobType": job_type if job_type else existing_filter.get("jobType"),
        "laborType": labor_type if labor_type else existing_filter.get("laborType"),
        "readyToWork": ready_to_work
        if ready_to_work is not None
        else existing_filter.get("readyToWork"),
        "finalBillMonth": final_bill_month
        if final_bill_month
        else existing_filter.get("finalBillMonth"),
        "minSellingAmount": min_selling_amount
        if min_selling_amount is not None
        else existing_filter.get("minSellingAmount"),
        "maxSellingAmount": max_selling_amount
        if max_selling_amount is not None
        else existing_filter.get("maxSellingAmount"),
        "limit": max_limit,
    }

    logger.info("[filter_jobs] Merged filter (additive): %s", active_filter)

    # Update the ContextVar for any subsequent tool calls in same turn
    current_active_filter.set(active_filter)

    # Build description for user
    filter_parts = []
    if customer_name:
        filter_parts.append(f"customer: {customer_name}")
    if job_type:
        filter_parts.append(f"{job_type}")
    if labor_type:
        filter_parts.append(f"{labor_type}")
    if ready_to_work is not None:
        filter_parts.append("ready to work" if ready_to_work else "not ready")
    if final_bill_month:
        filter_parts.append(f"billing in {final_bill_month}")
    if min_selling_amount is not None:
        filter_parts.append(f"over ${min_selling_amount:,.0f}")
    if max_selling_amount is not None:
        filter_parts.append(f"under ${max_selling_amount:,.0f}")

    filter_desc = ", ".join(filter_parts) if filter_parts else "all jobs"

    return {
        "message": f"Loading jobs: {filter_desc} (max {max_limit}). Dashboard is updating...",
        "activeFilter": active_filter,
    }


@tool(
    name="reset_job_filters",
    description="Clear all filters and show all backlog jobs. Use this when user says 'clear', 'reset', 'show all jobs', or 'start over'.",
)
def reset_job_filters() -> dict:
    """Clear all filters and reset to showing all jobs."""
    logger.info("[reset_job_filters] Clearing all filters")

    # Clear the ContextVar
    current_active_filter.set(None)

    active_filter = {
        "customerName": None,
        "jobType": None,
        "laborType": None,
        "readyToWork": None,
        "finalBillMonth": None,
        "minSellingAmount": None,
        "maxSellingAmount": None,
        "limit": 100,
    }

    return {
        "message": "All filters cleared. Showing all backlog jobs.",
        "activeFilter": active_filter,
    }
