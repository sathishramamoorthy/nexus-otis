"""Utility modules for the logistics agent."""

# Shared data helpers and context vars
from .data_helpers import (
    _get_all_backlog_jobs,
    _get_all_flights,
    _get_available_routes,
    _get_backlog_customers,
    _get_backlog_summary,
    _get_backlog_utilization,
    _get_historical_data,
    _get_predictions,
    current_active_filter,
    current_selected_flight,
    get_backlog_job_by_id,
    get_flight_by_id_or_number,
)

# MCP client functions (HTTP-based)
from .mcp_client import (
    # Flights - async
    get_all_flights_from_mcp,
    get_flight_by_id_from_mcp,
    get_flight_summary_from_mcp,
    get_flights_from_mcp,
    get_historical_from_mcp,
    get_predictions_from_mcp,
    get_routes_from_mcp,
    # Flights - sync
    get_all_flights_sync,
    get_flight_by_id_sync,
    get_flight_summary_sync,
    get_flights_sync,
    get_historical_sync,
    get_predictions_sync,
    get_routes_sync,
    # Backlog - async
    get_all_backlog_jobs_from_mcp,
    get_backlog_customers_from_mcp,
    get_backlog_job_by_id_from_mcp,
    get_backlog_jobs_from_mcp,
    get_backlog_summary_from_mcp,
    get_backlog_utilization_from_mcp,
    update_backlog_job_status_from_mcp,
    # Backlog - sync
    get_all_backlog_jobs_sync,
    get_backlog_customers_sync,
    get_backlog_job_by_id_sync,
    get_backlog_jobs_sync,
    get_backlog_summary_sync,
    get_backlog_utilization_sync,
    update_backlog_job_status_sync,
)

__all__ = [
    # Data helpers - flights
    "current_active_filter",
    "current_selected_flight",
    "_get_all_flights",
    "get_flight_by_id_or_number",
    "_get_historical_data",
    "_get_predictions",
    "_get_available_routes",
    # Data helpers - backlog
    "_get_all_backlog_jobs",
    "_get_backlog_summary",
    "_get_backlog_customers",
    "_get_backlog_utilization",
    "get_backlog_job_by_id",
    # MCP client functions - flights (async)
    "get_flights_from_mcp",
    "get_flight_by_id_from_mcp",
    "get_flight_summary_from_mcp",
    "get_all_flights_from_mcp",
    "get_historical_from_mcp",
    "get_predictions_from_mcp",
    "get_routes_from_mcp",
    # MCP client functions - flights (sync)
    "get_flights_sync",
    "get_all_flights_sync",
    "get_flight_by_id_sync",
    "get_flight_summary_sync",
    "get_historical_sync",
    "get_predictions_sync",
    "get_routes_sync",
    # MCP client functions - backlog (async)
    "get_backlog_jobs_from_mcp",
    "get_backlog_job_by_id_from_mcp",
    "get_backlog_summary_from_mcp",
    "get_all_backlog_jobs_from_mcp",
    "get_backlog_customers_from_mcp",
    "get_backlog_utilization_from_mcp",
    "update_backlog_job_status_from_mcp",
    # MCP client functions - backlog (sync)
    "get_backlog_jobs_sync",
    "get_backlog_job_by_id_sync",
    "get_backlog_summary_sync",
    "get_all_backlog_jobs_sync",
    "get_backlog_customers_sync",
    "get_backlog_utilization_sync",
    "update_backlog_job_status_sync",
]
