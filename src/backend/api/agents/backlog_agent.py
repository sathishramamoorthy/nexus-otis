"""
Backlog Agent with Microsoft Agent Framework

This module defines the backlog agent configuration and state schema
for the workable backlog dashboard backed by v2 Responses API.

Tools are imported from the tools/ directory.
"""

from __future__ import annotations

import logging
from pathlib import Path

from agent_framework import Agent, SupportsChatGetResponse
from agent_framework_ag_ui import AgentFrameworkAgent

from patches.agui_event_stream import attach_agui_context_sync

# Import backlog-specific tools
from .tools import analyze_backlog
from .tools.backlog_filter_tools import filter_jobs, reset_job_filters

logger = logging.getLogger(__name__)


# State schema for the backlog agent
STATE_SCHEMA: dict[str, object] = {
    "jobs": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "jobId": {"type": "string"},
                "jobType": {"type": "string"},
                "customerName": {"type": "string"},
                "jobSiteAddress": {"type": "string"},
                "projectDescription": {"type": "string"},
                "sellingAmount": {"type": "number"},
                "workableBacklogAmount": {"type": "number"},
                "projectedMargin": {"type": "number"},
                "scheduledStartDate": {"type": "string"},
                "projectedCompletionDate": {"type": "string"},
                "finalBillMonth": {"type": "string"},
                "laborType": {"type": "string"},
                "readyToWork": {"type": "boolean"},
                "downPaymentReceived": {"type": "boolean"},
                "permitReceived": {"type": "boolean"},
                "materialOnHand": {"type": "boolean"},
            },
        },
        "description": "List of backlog jobs to display in the dashboard.",
    },
    "selectedJob": {
        "type": "object",
        "description": "The currently selected job for detailed view.",
    },
    "utilizationData": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "weekStartDate": {"type": "string"},
                "weekEndDate": {"type": "string"},
                "crewScheduledHours": {"type": "number"},
                "crewUtilizationPercent": {"type": "number"},
                "mechanicScheduledHours": {"type": "number"},
                "mechanicUtilizationPercent": {"type": "number"},
                "overallUtilizationPercent": {"type": "number"},
                "jobsScheduled": {"type": "number"},
            },
        },
        "description": "Weekly resource utilization data for charts.",
    },
    "activeFilter": {
        "type": "object",
        "properties": {
            "customerName": {"type": "string"},
            "jobType": {"type": "string"},
            "laborType": {"type": "string"},
            "readyToWork": {"type": "boolean"},
            "finalBillMonth": {"type": "string"},
            "minSellingAmount": {"type": "number"},
            "maxSellingAmount": {"type": "number"},
            "limit": {"type": "number"},
        },
        "description": "Current filter state for the dashboard. Frontend reacts to this and fetches data via REST API.",
    },
}


def _load_system_prompt() -> str:
    """Load system prompt from markdown file."""
    prompt_path = Path(__file__).parent / "prompts" / "backlog_agent.md"
    return prompt_path.read_text(encoding="utf-8").strip()


def create_backlog_agent(chat_client: SupportsChatGetResponse) -> AgentFrameworkAgent:
    """Instantiate the Backlog agent backed by Microsoft Agent Framework."""
    base_agent = Agent(
        client=chat_client,
        name="backlog-agent",
        instructions=_load_system_prompt(),
        tools=[
            # Dashboard filter tools - these set activeFilter in state
            filter_jobs,
            reset_job_filters,
            # Analysis tools - answer questions about backlog data
            analyze_backlog,
        ],
    )

    agui_agent = AgentFrameworkAgent(
        agent=base_agent,
        name="backlog_agent",
        description="Manages workable backlog data, job scheduling, and resource utilization analysis.",
        state_schema=STATE_SCHEMA,
        require_confirmation=False,
        use_service_session=True,
    )

    # Attach context sync for filter state
    attach_agui_context_sync(agui_agent)

    return agui_agent
