"""
Logistics MCP Server

An MCP server that exposes logistics flight data through MCP tools.
Uses DuckDB for SQL query capabilities on JSON data files.

Tools:
- get_tables: Gets the list of all tables and their schemas.
- query_data: Runs SQL queries on the flight data.

Resources:
- tables: Gets the list of all tables in the database.

REST API Endpoints (Flights):
- GET /api/flights: Get flights with filtering and pagination
- GET /api/flights/{id}: Get a specific flight by ID
- GET /api/summary: Get flight data summary
- GET /api/historical: Get historical payload data (with optional route filter)
- GET /api/predictions: Get predicted payload data for future flights
- GET /api/routes: Get list of available routes with statistics

REST API Endpoints (Backlog):
- GET /api/backlog: Get backlog jobs with filtering and pagination
- GET /api/backlog/{job_id}: Get a specific job by ID
- GET /api/backlog-summary: Get backlog data summary
- GET /api/backlog-customers: Get customer consolidated view
- GET /api/backlog-utilization: Get resource scheduling data

DuckDB Tables:
- flights: Current flight data
- historical_data: Historical and predicted payload data (date, route, pounds, cubicFeet, predicted)
- oneview: OneView integration data
- utilization: Utilization tracking data
- backlog: Job/project backlog data (jobId, customerName, sellingAmount, workableBacklogAmount, etc.)
- backlog_oneview: Customer consolidated view (customerId, totalJobs, totalContractValue, workableBacklog)
- backlog_utilization: Resource scheduling data (weekStartDate, crewScheduledHours, utilizationPercent)

Transport: HTTP/SSE
Default URL: http://localhost:8001
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import duckdb
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from auth import EntraIDAuthMiddleware, is_auth_enabled

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

# Server configuration
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))

# Data file paths - local to MCP server
DATA_DIR = Path(__file__).parent / "data"
FLIGHTS_FILE = DATA_DIR / "flights.json"
ONEVIEW_FILE = DATA_DIR / "oneview.json"
UTILIZATION_FILE = DATA_DIR / "utilization.json"

# Backlog data files
BACKLOG_FILE = DATA_DIR / "backlog.json"
BACKLOG_ONEVIEW_FILE = DATA_DIR / "backlogoneview.json"
BACKLOG_UTILIZATION_FILE = DATA_DIR / "backlogutilization.json"

# Historical data cache (loaded from flights.json)
_HISTORICAL_DATA_CACHE: list = []

# Cache for flight data (used by REST endpoints)
_FLIGHT_DATA_CACHE: dict = {}

# Cache for backlog data (used by REST endpoints)
_BACKLOG_CACHE: list = []
_BACKLOG_ONEVIEW_CACHE: list = []
_BACKLOG_UTILIZATION_CACHE: list = []


class LogisticsMCP:
    """MCP server for logistics flight data using DuckDB."""

    def __init__(self):
        self._duckdb_conn: duckdb.DuckDBPyConnection | None = None

    def init(self):
        """Initialize the DuckDB connection with flight data."""
        self._get_connection()

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create the DuckDB connection with loaded data."""
        if self._duckdb_conn is not None:
            return self._duckdb_conn

        logger.info("Initializing DuckDB with JSON data files")
        self._duckdb_conn = duckdb.connect(":memory:")

        # Load flights data - the JSON has structure {"flights": [...]}
        if FLIGHTS_FILE.exists():
            self._duckdb_conn.execute(f"""
                CREATE TABLE flights AS
                SELECT unnest(flights) AS flight FROM read_json_auto('{FLIGHTS_FILE}')
            """)
            # Flatten the nested structure
            self._duckdb_conn.execute("""
                CREATE OR REPLACE TABLE flights AS
                SELECT
                    flight.id as id,
                    flight.flightNumber as flightNumber,
                    flight.flightDate as flightDate,
                    flight."from" as origin,
                    flight."to" as destination,
                    flight.currentPounds as currentPounds,
                    flight.maxPounds as maxPounds,
                    flight.currentCubicFeet as currentCubicFeet,
                    flight.maxCubicFeet as maxCubicFeet,
                    flight.utilizationPercent as utilizationPercent,
                    flight.riskLevel as riskLevel,
                    flight.sortTime as sortTime
                FROM flights
            """)
            count = self._duckdb_conn.execute("SELECT COUNT(*) FROM flights").fetchone()
            logger.info(f"Loaded {count[0] if count else 0} flights into DuckDB")

        # Load oneview data if exists
        if ONEVIEW_FILE.exists():
            try:
                self._duckdb_conn.execute(f"""
                    CREATE TABLE oneview AS
                    SELECT * FROM read_json_auto('{ONEVIEW_FILE}')
                """)
                count = self._duckdb_conn.execute("SELECT COUNT(*) FROM oneview").fetchone()
                logger.info(f"Loaded {count[0] if count else 0} oneview records into DuckDB")
            except Exception as e:
                logger.warning(f"Could not load oneview.json: {e}")

        # Load utilization data if exists
        if UTILIZATION_FILE.exists():
            try:
                self._duckdb_conn.execute(f"""
                    CREATE TABLE utilization AS
                    SELECT * FROM read_json_auto('{UTILIZATION_FILE}')
                """)
                count = self._duckdb_conn.execute("SELECT COUNT(*) FROM utilization").fetchone()
                logger.info(f"Loaded {count[0] if count else 0} utilization records into DuckDB")
            except Exception as e:
                logger.warning(f"Could not load utilization.json: {e}")

        # Load backlog data (job/project backlog)
        if BACKLOG_FILE.exists():
            try:
                self._duckdb_conn.execute(f"""
                    CREATE TABLE backlog AS
                    SELECT * FROM read_json_auto('{BACKLOG_FILE}')
                """)
                count = self._duckdb_conn.execute("SELECT COUNT(*) FROM backlog").fetchone()
                logger.info(f"Loaded {count[0] if count else 0} backlog records into DuckDB")
            except Exception as e:
                logger.warning(f"Could not load backlog.json: {e}")

        # Load backlog oneview data (customer consolidated view)
        if BACKLOG_ONEVIEW_FILE.exists():
            try:
                self._duckdb_conn.execute(f"""
                    CREATE TABLE backlog_oneview AS
                    SELECT * FROM read_json_auto('{BACKLOG_ONEVIEW_FILE}')
                """)
                count = self._duckdb_conn.execute("SELECT COUNT(*) FROM backlog_oneview").fetchone()
                logger.info(
                    f"Loaded {count[0] if count else 0} backlog_oneview records into DuckDB"
                )
            except Exception as e:
                logger.warning(f"Could not load backlogoneview.json: {e}")

        # Load backlog utilization data (resource scheduling)
        if BACKLOG_UTILIZATION_FILE.exists():
            try:
                self._duckdb_conn.execute(f"""
                    CREATE TABLE backlog_utilization AS
                    SELECT * FROM read_json_auto('{BACKLOG_UTILIZATION_FILE}')
                """)
                count = self._duckdb_conn.execute(
                    "SELECT COUNT(*) FROM backlog_utilization"
                ).fetchone()
                logger.info(
                    f"Loaded {count[0] if count else 0} backlog_utilization records into DuckDB"
                )
            except Exception as e:
                logger.warning(f"Could not load backlogutilization.json: {e}")

        # Load historical data from flights.json (historicalData array)
        if FLIGHTS_FILE.exists():
            try:
                # Read the JSON file and extract historicalData
                with open(FLIGHTS_FILE, encoding="utf-8") as f:
                    data = json.load(f)
                historical = data.get("historicalData", [])

                if historical:
                    # Create table from the historical data
                    self._duckdb_conn.execute("""
                        CREATE TABLE historical_data (
                            date VARCHAR,
                            route VARCHAR,
                            pounds INTEGER,
                            cubicFeet INTEGER,
                            predicted BOOLEAN
                        )
                    """)

                    # Insert historical data
                    for record in historical:
                        self._duckdb_conn.execute(
                            "INSERT INTO historical_data VALUES (?, ?, ?, ?, ?)",
                            [
                                record.get("date"),
                                record.get("route"),
                                record.get("pounds"),
                                record.get("cubicFeet"),
                                record.get("predicted", False),
                            ],
                        )

                    count = self._duckdb_conn.execute(
                        "SELECT COUNT(*) FROM historical_data"
                    ).fetchone()
                    logger.info(f"Loaded {count[0] if count else 0} historical records into DuckDB")
            except Exception as e:
                logger.warning(f"Could not load historical data: {e}")

        return self._duckdb_conn

    def get_tables(self) -> str:
        """Gets the list of all tables and their schemas."""
        try:
            conn = self._get_connection()
            result = conn.execute("SHOW TABLES").fetchall()
            tables = [row[0] for row in result]

            # Get schema for each table
            table_info = {}
            for table in tables:
                schema = conn.execute(f"DESCRIBE {table}").fetchall()
                table_info[table] = [{"column": row[0], "type": row[1]} for row in schema]

            return json.dumps(
                {
                    "tables": tables,
                    "schemas": table_info,
                }
            )
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return json.dumps({"error": str(e)})

    def query_data(self, query: str) -> str:
        """Runs SQL queries on the flight data.

        Args:
            query: SQL query to execute. Available tables: 'flights' with columns
                   (id, flightNumber, flightDate, origin, destination, currentPounds,
                   maxPounds, currentCubicFeet, maxCubicFeet, utilizationPercent,
                   riskLevel, sortTime).

        Returns:
            JSON string with columns and rows from the query result.
        """
        try:
            conn = self._get_connection()
            result = conn.execute(query)
            colnames = [desc[0] for desc in result.description]
            rows = result.fetchall()

            # Convert rows to serializable format
            serializable_rows = []
            for row in rows:
                row_data = []
                for val in row:
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    row_data.append(val)
                serializable_rows.append(row_data)

            return json.dumps(
                {
                    "columns": colnames,
                    "rows": serializable_rows,
                    "row_count": len(rows),
                }
            )
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return json.dumps({"error": str(e)})

    def get_tables_resource(self) -> str:
        """Gets list of tables as a resource."""
        return self.get_tables()


# ============================================================================
# REST API Functions (for direct HTTP access - used by MCP client)
# ============================================================================


def _load_flight_data() -> dict:
    """Load and cache flight data from the JSON file."""
    global _HISTORICAL_DATA_CACHE
    if not _FLIGHT_DATA_CACHE:
        logger.info(f"Loading flight data from {FLIGHTS_FILE}")
        with open(FLIGHTS_FILE, encoding="utf-8") as f:
            data = json.load(f)
            # Also cache historical data
            if not _HISTORICAL_DATA_CACHE:
                _HISTORICAL_DATA_CACHE = data.get("historicalData", [])
                logger.info(f"Loaded {len(_HISTORICAL_DATA_CACHE)} historical records")
            _FLIGHT_DATA_CACHE.update(data)
        logger.info(f"Loaded {len(_FLIGHT_DATA_CACHE.get('flights', []))} flights")
    return _FLIGHT_DATA_CACHE


def get_flights(
    limit: int = 100,
    offset: int = 0,
    risk_level: str | None = None,
    utilization: str | None = None,
    route_from: str | None = None,
    route_to: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "utilizationPercent",
    sort_desc: bool = True,
) -> dict[str, Any]:
    """Get flights with filtering, sorting, and pagination."""
    data = _load_flight_data()
    all_flights = data.get("flights", [])

    # Apply filters
    filtered = all_flights

    if risk_level:
        filtered = [f for f in filtered if f.get("riskLevel") == risk_level]

    if utilization:
        if utilization == "over":
            filtered = [f for f in filtered if f.get("utilizationPercent", 0) > 95]
        elif utilization == "near_capacity":
            filtered = [f for f in filtered if 85 <= f.get("utilizationPercent", 0) <= 95]
        elif utilization == "under":
            filtered = [f for f in filtered if f.get("utilizationPercent", 0) < 50]
        elif utilization == "optimal":
            filtered = [f for f in filtered if 50 <= f.get("utilizationPercent", 0) < 85]

    if route_from:
        filtered = [f for f in filtered if f.get("from", "").upper() == route_from.upper()]

    if route_to:
        filtered = [f for f in filtered if f.get("to", "").upper() == route_to.upper()]

    if date_from:
        filtered = [f for f in filtered if f.get("flightDate", "") >= date_from]

    if date_to:
        filtered = [f for f in filtered if f.get("flightDate", "") <= date_to]

    # Sort
    if sort_by and filtered:
        filtered = sorted(
            filtered,
            key=lambda x: (
                x.get(sort_by, 0)
                if isinstance(x.get(sort_by), (int, float))
                else str(x.get(sort_by, ""))
            ),
            reverse=sort_desc,
        )

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "flights": paginated,
        "total": total,
        "query": {
            "limit": limit,
            "offset": offset,
            "risk_level": risk_level,
            "utilization": utilization,
            "route_from": route_from,
            "route_to": route_to,
            "date_from": date_from,
            "date_to": date_to,
        },
    }


def get_flight_by_id(flight_id: str) -> dict[str, Any]:
    """Get a specific flight by ID or flight number."""
    data = _load_flight_data()
    all_flights = data.get("flights", [])

    search = flight_id.upper().replace(" ", "").replace("-", "")
    for flight in all_flights:
        flight_num = flight.get("flightNumber", "").upper().replace("-", "")
        if flight.get("id") == flight_id or flight_num == search:
            return {"flight": flight}

    return {"flight": None, "error": f"Flight {flight_id} not found"}


def get_flight_summary() -> dict[str, Any]:
    """Get a summary of all available flight data."""
    data = _load_flight_data()
    flights = data.get("flights", [])

    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    route_counts: dict[str, int] = {}
    total_utilization = 0

    for f in flights:
        risk = f.get("riskLevel", "unknown")
        if risk in risk_counts:
            risk_counts[risk] += 1

        route = f"{f.get('from', '?')} → {f.get('to', '?')}"
        route_counts[route] = route_counts.get(route, 0) + 1
        total_utilization += f.get("utilizationPercent", 0)

    avg_utilization = total_utilization / len(flights) if flights else 0

    airports = set()
    for f in flights:
        airports.add(f.get("from", ""))
        airports.add(f.get("to", ""))
    airports.discard("")

    return {
        "totalFlights": len(flights),
        "riskBreakdown": risk_counts,
        "averageUtilization": round(avg_utilization, 1),
        "uniqueRoutes": len(route_counts),
        "topRoutes": sorted(route_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        "airports": sorted(list(airports)),
        "flightsAtRisk": risk_counts["high"] + risk_counts["critical"],
        "underUtilizedFlights": risk_counts["low"],
    }


def get_historical_data(
    days: int = 7,
    route: str | None = None,
    include_predictions: bool = True,
) -> dict[str, Any]:
    """Get historical payload data with optional route filtering.

    Args:
        days: Number of historical days to retrieve (default: 7)
        route: Optional route filter (e.g., 'LAX → ORD' or 'LAX-ORD')
        include_predictions: Whether to include prediction data (default: True)

    Returns:
        Dict with historical data, predictions, and summary statistics
    """
    _load_flight_data()  # Ensure data is loaded
    all_data = _HISTORICAL_DATA_CACHE.copy()

    # Filter by route if specified
    if route:
        # Normalize route format
        normalized = route.replace("-", " → ").replace("->", " → ").replace(" - ", " → ")
        all_data = [d for d in all_data if d.get("route") == normalized]

    # Separate historical and predicted data
    historical = [d for d in all_data if not d.get("predicted", False)]
    predictions = [d for d in all_data if d.get("predicted", False)]

    # Sort by date (descending for historical to get most recent first)
    historical = sorted(historical, key=lambda x: x.get("date", ""), reverse=True)
    predictions = sorted(predictions, key=lambda x: x.get("date", ""))

    # Limit historical to requested number of unique days (not records)
    if historical:
        unique_dates = sorted(set(d.get("date", "") for d in historical), reverse=True)[:days]
        historical = [d for d in historical if d.get("date", "") in unique_dates]
        # Re-sort ascending for display
        historical = sorted(historical, key=lambda x: x.get("date", ""))

    # Calculate statistics
    if historical:
        avg_pounds = sum(d.get("pounds", 0) for d in historical) // len(historical)
        avg_cubic = sum(d.get("cubicFeet", 0) for d in historical) // len(historical)
        unique_hist_dates = len(set(d.get("date", "") for d in historical))
    else:
        avg_pounds = 0
        avg_cubic = 0
        unique_hist_dates = 0

    unique_pred_dates = len(set(d.get("date", "") for d in predictions)) if predictions else 0

    result = {
        "historical": historical,
        "predictions": predictions if include_predictions else [],
        "summary": {
            "historicalDays": unique_hist_dates,
            "predictionDays": unique_pred_dates if include_predictions else 0,
            "averagePounds": avg_pounds,
            "averageCubicFeet": avg_cubic,
            "route": route,
        },
    }

    return result


def get_predictions(
    days: int = 7,
    route: str | None = None,
) -> dict[str, Any]:
    """Get predicted payload data for future flights.

    Args:
        days: Number of prediction days to retrieve (default: 7)
        route: Optional route filter (e.g., 'LAX → ORD')

    Returns:
        Dict with prediction data
    """
    _load_flight_data()  # Ensure data is loaded
    all_data = _HISTORICAL_DATA_CACHE.copy()

    # Filter by route if specified
    if route:
        normalized = route.replace("-", " → ").replace("->", " → ").replace(" - ", " → ")
        all_data = [d for d in all_data if d.get("route") == normalized]

    # Get only predictions
    predictions = [d for d in all_data if d.get("predicted", False)]
    predictions = sorted(predictions, key=lambda x: x.get("date", ""))
    predictions = predictions[:days]

    # Get unique routes in predictions
    routes = list(set(d.get("route", "") for d in predictions))

    return {
        "predictions": predictions,
        "totalPredictions": len(predictions),
        "routes": routes,
        "query": {
            "days": days,
            "route": route,
        },
    }


def get_available_routes() -> dict[str, Any]:
    """Get list of all available routes in historical data."""
    _load_flight_data()  # Ensure data is loaded

    routes: dict[str, dict] = {}
    for record in _HISTORICAL_DATA_CACHE:
        route = record.get("route", "")
        if route:
            if route not in routes:
                routes[route] = {
                    "historical_count": 0,
                    "prediction_count": 0,
                    "total_pounds": 0,
                }
            if record.get("predicted"):
                routes[route]["prediction_count"] += 1
            else:
                routes[route]["historical_count"] += 1
                routes[route]["total_pounds"] += record.get("pounds", 0)

    route_list = []
    for route, stats in routes.items():
        avg_pounds = stats["total_pounds"] // max(1, stats["historical_count"])
        route_list.append(
            {
                "route": route,
                "historicalRecords": stats["historical_count"],
                "predictionRecords": stats["prediction_count"],
                "averagePounds": avg_pounds,
            }
        )

    return {
        "routes": sorted(route_list, key=lambda x: x["historicalRecords"], reverse=True),
        "totalRoutes": len(route_list),
    }


# ============================================================================
# Backlog REST API Functions (for workable backlog data)
# ============================================================================


def _load_backlog_data() -> list:
    """Load and cache backlog data from JSON files."""
    global _BACKLOG_CACHE, _BACKLOG_ONEVIEW_CACHE, _BACKLOG_UTILIZATION_CACHE

    if not _BACKLOG_CACHE and BACKLOG_FILE.exists():
        logger.info(f"Loading backlog data from {BACKLOG_FILE}")
        with open(BACKLOG_FILE, encoding="utf-8") as f:
            _BACKLOG_CACHE = json.load(f)
        logger.info(f"Loaded {len(_BACKLOG_CACHE)} backlog jobs")

    if not _BACKLOG_ONEVIEW_CACHE and BACKLOG_ONEVIEW_FILE.exists():
        logger.info(f"Loading backlog oneview data from {BACKLOG_ONEVIEW_FILE}")
        with open(BACKLOG_ONEVIEW_FILE, encoding="utf-8") as f:
            _BACKLOG_ONEVIEW_CACHE = json.load(f)
        logger.info(f"Loaded {len(_BACKLOG_ONEVIEW_CACHE)} customer records")

    if not _BACKLOG_UTILIZATION_CACHE and BACKLOG_UTILIZATION_FILE.exists():
        logger.info(f"Loading backlog utilization data from {BACKLOG_UTILIZATION_FILE}")
        with open(BACKLOG_UTILIZATION_FILE, encoding="utf-8") as f:
            _BACKLOG_UTILIZATION_CACHE = json.load(f)
        logger.info(f"Loaded {len(_BACKLOG_UTILIZATION_CACHE)} utilization records")

    return _BACKLOG_CACHE


def get_backlog_jobs(
    limit: int = 100,
    offset: int = 0,
    job_type: str | None = None,
    ready_to_work: bool | None = None,
    customer_name: str | None = None,
    labor_type: str | None = None,
    final_bill_month: str | None = None,
    min_selling_amount: float | None = None,
    max_selling_amount: float | None = None,
    sort_by: str = "sellingAmount",
    sort_desc: bool = True,
) -> dict[str, Any]:
    """Get backlog jobs with filtering, sorting, and pagination."""
    _load_backlog_data()
    all_jobs = _BACKLOG_CACHE.copy()

    # Apply filters
    filtered = all_jobs

    if job_type:
        filtered = [j for j in filtered if j.get("jobType") == job_type]

    if ready_to_work is not None:
        filtered = [j for j in filtered if j.get("readyToWork") == ready_to_work]

    if customer_name:
        search = customer_name.lower()
        filtered = [j for j in filtered if search in j.get("customerName", "").lower()]

    if labor_type:
        filtered = [j for j in filtered if j.get("laborType") == labor_type]

    if final_bill_month:
        filtered = [j for j in filtered if j.get("finalBillMonth") == final_bill_month]

    if min_selling_amount is not None:
        filtered = [j for j in filtered if j.get("sellingAmount", 0) >= min_selling_amount]

    if max_selling_amount is not None:
        filtered = [j for j in filtered if j.get("sellingAmount", 0) <= max_selling_amount]

    # Sort
    if sort_by and filtered:
        filtered = sorted(
            filtered,
            key=lambda x: (
                x.get(sort_by, 0)
                if isinstance(x.get(sort_by), (int, float))
                else str(x.get(sort_by, ""))
            ),
            reverse=sort_desc,
        )

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "jobs": paginated,
        "total": total,
        "query": {
            "limit": limit,
            "offset": offset,
            "job_type": job_type,
            "ready_to_work": ready_to_work,
            "customer_name": customer_name,
            "labor_type": labor_type,
            "final_bill_month": final_bill_month,
        },
    }


def get_backlog_job_by_id(job_id: str) -> dict[str, Any]:
    """Get a specific backlog job by ID."""
    _load_backlog_data()

    for job in _BACKLOG_CACHE:
        if job.get("jobId") == job_id:
            return {"job": job}

    return {"job": None, "error": f"Job {job_id} not found"}


def update_backlog_job_status(
    job_id: str,
    down_payment_received: bool | None = None,
    permit_received: bool | None = None,
    material_ordered: bool | None = None,
    material_on_hand: bool | None = None,
    customer_delay: bool | None = None,
) -> dict[str, Any]:
    """Update status fields for a backlog job and recompute readyToWork."""
    global _BACKLOG_CACHE
    _load_backlog_data()

    for job in _BACKLOG_CACHE:
        if job.get("jobId") == job_id:
            # Update only provided fields
            if down_payment_received is not None:
                job["downPaymentReceived"] = down_payment_received
            if permit_received is not None:
                job["permitReceived"] = permit_received
            if material_ordered is not None:
                job["materialOrdered"] = material_ordered
            if material_on_hand is not None:
                job["materialOnHand"] = material_on_hand
            if customer_delay is not None:
                job["customerDelay"] = customer_delay

            # Recompute readyToWork based on conditions
            # Ready if: payment received, permit received, material on hand, no customer delay
            job["readyToWork"] = (
                job.get("downPaymentReceived", False)
                and job.get("permitReceived", False)
                and job.get("materialOnHand", False)
                and not job.get("customerDelay", False)
            )

            return {"job": job, "updated": True}

    return {"job": None, "error": f"Job {job_id} not found", "updated": False}


def get_backlog_summary() -> dict[str, Any]:
    """Get a summary of all backlog data."""
    _load_backlog_data()

    total_selling = 0
    total_workable = 0
    total_projected_margin = 0
    job_type_counts: dict[str, int] = {}
    labor_type_counts: dict[str, int] = {}
    month_counts: dict[str, float] = {}
    ready_count = 0
    not_ready_count = 0

    for job in _BACKLOG_CACHE:
        total_selling += job.get("sellingAmount", 0)
        total_workable += job.get("workableBacklogAmount", 0)
        total_projected_margin += job.get("projectedMargin", 0)

        job_type = job.get("jobType", "Unknown")
        job_type_counts[job_type] = job_type_counts.get(job_type, 0) + 1

        labor = job.get("laborType", "Unknown")
        labor_type_counts[labor] = labor_type_counts.get(labor, 0) + 1

        month = job.get("finalBillMonth", "Unknown")
        month_counts[month] = month_counts.get(month, 0) + job.get("sellingAmount", 0)

        if job.get("readyToWork"):
            ready_count += 1
        else:
            not_ready_count += 1

    # Get unique customers
    customers = set(job.get("customerName", "") for job in _BACKLOG_CACHE)
    customers.discard("")

    return {
        "totalJobs": len(_BACKLOG_CACHE),
        "totalSellingAmount": round(total_selling, 2),
        "totalWorkableBacklog": round(total_workable, 2),
        "totalProjectedMargin": round(total_projected_margin, 2),
        "averageJobValue": round(total_selling / len(_BACKLOG_CACHE), 2) if _BACKLOG_CACHE else 0,
        "jobTypeBreakdown": job_type_counts,
        "laborTypeBreakdown": labor_type_counts,
        "revenueByMonth": {k: round(v, 2) for k, v in sorted(month_counts.items())},
        "readyToWork": ready_count,
        "notReadyToWork": not_ready_count,
        "uniqueCustomers": len(customers),
    }


def get_backlog_customers() -> dict[str, Any]:
    """Get customer consolidated view from backlog oneview data."""
    _load_backlog_data()

    return {
        "customers": _BACKLOG_ONEVIEW_CACHE,
        "totalCustomers": len(_BACKLOG_ONEVIEW_CACHE),
        "totalContractValue": sum(c.get("totalContractValue", 0) for c in _BACKLOG_ONEVIEW_CACHE),
        "totalWorkableBacklog": sum(c.get("workableBacklog", 0) for c in _BACKLOG_ONEVIEW_CACHE),
    }


def get_backlog_utilization(
    week_start: str | None = None,
    week_end: str | None = None,
) -> dict[str, Any]:
    """Get resource utilization data for backlog scheduling."""
    _load_backlog_data()

    filtered = _BACKLOG_UTILIZATION_CACHE.copy()

    if week_start:
        filtered = [u for u in filtered if u.get("weekStartDate", "") >= week_start]

    if week_end:
        filtered = [u for u in filtered if u.get("weekEndDate", "") <= week_end]

    # Calculate averages
    if filtered:
        avg_crew_util = sum(u.get("crewUtilizationPercent", 0) for u in filtered) / len(filtered)
        avg_mechanic_util = sum(u.get("mechanicUtilizationPercent", 0) for u in filtered) / len(
            filtered
        )
        avg_overall_util = sum(u.get("overallUtilizationPercent", 0) for u in filtered) / len(
            filtered
        )
        total_scheduled_hours = sum(u.get("totalScheduledHours", 0) for u in filtered)
    else:
        avg_crew_util = 0
        avg_mechanic_util = 0
        avg_overall_util = 0
        total_scheduled_hours = 0

    return {
        "utilization": filtered,
        "totalWeeks": len(filtered),
        "averageCrewUtilization": round(avg_crew_util, 1),
        "averageMechanicUtilization": round(avg_mechanic_util, 1),
        "averageOverallUtilization": round(avg_overall_util, 1),
        "totalScheduledHours": total_scheduled_hours,
        "query": {
            "week_start": week_start,
            "week_end": week_end,
        },
    }


# ============================================================================
# REST API Endpoints (Starlette)
# ============================================================================


async def rest_get_historical(request: Request) -> JSONResponse:
    """REST endpoint for getting historical data."""
    params = request.query_params
    result = get_historical_data(
        days=int(params.get("days", 7)),
        route=params.get("route"),
        include_predictions=params.get("include_predictions", "true").lower() == "true",
    )
    return JSONResponse(result)


async def rest_get_predictions(request: Request) -> JSONResponse:
    """REST endpoint for getting predictions."""
    params = request.query_params
    result = get_predictions(
        days=int(params.get("days", 7)),
        route=params.get("route"),
    )
    return JSONResponse(result)


async def rest_get_routes(request: Request) -> JSONResponse:
    """REST endpoint for getting available routes."""
    result = get_available_routes()
    return JSONResponse(result)


async def rest_get_flights(request: Request) -> JSONResponse:
    """REST endpoint for getting flights."""
    params = request.query_params
    result = get_flights(
        limit=int(params.get("limit", 100)),
        offset=int(params.get("offset", 0)),
        risk_level=params.get("risk_level"),
        utilization=params.get("utilization"),
        route_from=params.get("route_from"),
        route_to=params.get("route_to"),
        date_from=params.get("date_from"),
        date_to=params.get("date_to"),
        sort_by=params.get("sort_by", "utilizationPercent"),
        sort_desc=params.get("sort_desc", "true").lower() == "true",
    )
    return JSONResponse(result)


async def rest_get_flight(request: Request) -> JSONResponse:
    """REST endpoint for getting a single flight."""
    flight_id = request.path_params["flight_id"]
    result = get_flight_by_id(flight_id)
    return JSONResponse(result)


async def rest_get_summary(request: Request) -> JSONResponse:
    """REST endpoint for getting flight summary."""
    result = get_flight_summary()
    return JSONResponse(result)


# ============================================================================
# Backlog REST API Endpoints (Starlette)
# ============================================================================


async def rest_get_backlog_jobs(request: Request) -> JSONResponse:
    """REST endpoint for getting backlog jobs."""
    params = request.query_params
    result = get_backlog_jobs(
        limit=int(params.get("limit", 100)),
        offset=int(params.get("offset", 0)),
        job_type=params.get("job_type"),
        ready_to_work=params.get("ready_to_work", "").lower() == "true"
        if params.get("ready_to_work")
        else None,
        customer_name=params.get("customer_name"),
        labor_type=params.get("labor_type"),
        final_bill_month=params.get("final_bill_month"),
        min_selling_amount=float(min_sell)
        if (min_sell := params.get("min_selling_amount"))
        else None,
        max_selling_amount=float(max_sell)
        if (max_sell := params.get("max_selling_amount"))
        else None,
        sort_by=params.get("sort_by", "sellingAmount"),
        sort_desc=params.get("sort_desc", "true").lower() == "true",
    )
    return JSONResponse(result)


async def rest_get_backlog_job(request: Request) -> JSONResponse:
    """REST endpoint for getting a single backlog job."""
    job_id = request.path_params["job_id"]
    result = get_backlog_job_by_id(job_id)
    return JSONResponse(result)


async def rest_patch_backlog_job(request: Request) -> JSONResponse:
    """REST endpoint for updating a backlog job's status fields."""
    job_id = request.path_params["job_id"]
    body = await request.json()

    result = update_backlog_job_status(
        job_id=job_id,
        down_payment_received=body.get("downPaymentReceived"),
        permit_received=body.get("permitReceived"),
        material_ordered=body.get("materialOrdered"),
        material_on_hand=body.get("materialOnHand"),
        customer_delay=body.get("customerDelay"),
    )

    if result.get("error"):
        return JSONResponse(result, status_code=404)
    return JSONResponse(result)


async def rest_get_backlog_summary(request: Request) -> JSONResponse:
    """REST endpoint for getting backlog summary."""
    result = get_backlog_summary()
    return JSONResponse(result)


async def rest_get_backlog_customers(request: Request) -> JSONResponse:
    """REST endpoint for getting backlog customer view."""
    result = get_backlog_customers()
    return JSONResponse(result)


async def rest_get_backlog_utilization(request: Request) -> JSONResponse:
    """REST endpoint for getting backlog utilization."""
    params = request.query_params
    result = get_backlog_utilization(
        week_start=params.get("week_start"),
        week_end=params.get("week_end"),
    )
    return JSONResponse(result)


async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint."""
    data = _load_flight_data()
    return JSONResponse(
        {
            "status": "healthy",
            "server": "logistics-mcp",
            "transport": "http/sse",
            "flights_loaded": len(data.get("flights", [])),
            "historical_records": len(_HISTORICAL_DATA_CACHE),
            "backlog_jobs": len(_BACKLOG_CACHE),
            "backlog_customers": len(_BACKLOG_ONEVIEW_CACHE),
            "backlog_utilization_weeks": len(_BACKLOG_UTILIZATION_CACHE),
            "auth_enabled": is_auth_enabled(),
        }
    )


# Create Starlette app with REST routes
rest_app = Starlette(
    debug=True,
    routes=[
        Route("/health", health_check, methods=["GET"]),
        # Flight endpoints
        Route("/api/flights", rest_get_flights, methods=["GET"]),
        Route("/api/flights/{flight_id:str}", rest_get_flight, methods=["GET"]),
        Route("/api/summary", rest_get_summary, methods=["GET"]),
        Route("/api/historical", rest_get_historical, methods=["GET"]),
        Route("/api/predictions", rest_get_predictions, methods=["GET"]),
        Route("/api/routes", rest_get_routes, methods=["GET"]),
        # Backlog endpoints
        Route("/api/backlog", rest_get_backlog_jobs, methods=["GET"]),
        Route("/api/backlog/{job_id:str}", rest_get_backlog_job, methods=["GET"]),
        Route("/api/backlog/{job_id:str}", rest_patch_backlog_job, methods=["PATCH"]),
        Route("/api/backlog-summary", rest_get_backlog_summary, methods=["GET"]),
        Route("/api/backlog-customers", rest_get_backlog_customers, methods=["GET"]),
        Route("/api/backlog-utilization", rest_get_backlog_utilization, methods=["GET"]),
    ],
)

# Add authentication middleware
rest_app.add_middleware(EntraIDAuthMiddleware)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Logistics MCP Server on {MCP_HOST}:{MCP_PORT}")
    logger.info(f"REST API: http://{MCP_HOST}:{MCP_PORT}/api/flights")
    logger.info(f"Backlog API: http://{MCP_HOST}:{MCP_PORT}/api/backlog")

    # Pre-load flight data
    _load_flight_data()

    # Pre-load backlog data
    _load_backlog_data()

    uvicorn.run(rest_app, host=MCP_HOST, port=MCP_PORT)
