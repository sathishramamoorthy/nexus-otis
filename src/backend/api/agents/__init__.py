"""
Agents package for the CopilotKit + Microsoft Agent Framework API.

Contains:
- logistics_agent.py: Logistics dashboard agent with flight payload tools
- backlog_agent.py: Workable backlog dashboard agent with job scheduling tools
"""

from agents.backlog_agent import create_backlog_agent
from agents.logistics_agent import create_logistics_agent

__all__ = ["create_logistics_agent", "create_backlog_agent"]
