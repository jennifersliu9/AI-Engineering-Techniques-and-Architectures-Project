"""Prove the agent discovers and calls tools through the MCP protocol."""

import importlib.util

import pytest

from harborline.agent import run_agent
from harborline.mcp_client import InProcessMcpBus, StdioMcpBus
from harborline.mcp_server import MCP_TOOL_NAMES


pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("mcp") is None,
    reason="mcp package is not installed",
)


def test_inprocess_mcp_discover_and_call():
    bus = InProcessMcpBus()
    try:
        assert set(MCP_TOOL_NAMES) <= set(bus.discovered_tools)
        assert len(bus.discovered_tools) >= 5
        profile = bus.call("lookup_employee_profile", employee_id="EMP-1008")
        assert profile["found"] is True
        assert profile["employee"]["legal_name"] == "Alex Kim"
        hits = bus.call("search_policy_documents", query="PTO carryover 40 hours", kind="policy")
        assert hits["hits"]
        ticket = bus.call(
            "create_mock_hr_ticket",
            topic="pto_request",
            summary="Friday off",
            employee_id="EMP-1008",
            confirm=False,
        )
        assert ticket["status"] == "pending_confirmation"
        assert ticket["draft"]["writes_to_harborhub"] is False
    finally:
        bus.close()


def test_stdio_mcp_discover_and_agent_call():
    bus = StdioMcpBus(extra_env={"HARBORLINE_RETRIEVE_BACKEND": "tfidf"})
    try:
        if not bus.available:
            pytest.skip(f"stdio MCP server did not start: {getattr(bus, '_error', None)}")
        assert len(bus.discovered_tools) >= 5
        assert "search_policy_documents" in bus.discovered_tools
        assert "check_pto_balance" in bus.discovered_tools
        listed = bus.call("lookup_employee_profile", employee_id="EMP-1014")
        assert listed["found"] is True
        result = run_agent(
            "Can I take PTO next week?",
            employee_id="EMP-1014",
            bus=bus,
        )
        assert result.tool_transport == "mcp-stdio"
        assert result.discovered_tools
        tools = [s.tool for s in result.steps]
        assert "lookup_employee_profile" in tools
        assert "check_pto_balance" in tools
        assert all(s.ok for s in result.steps)
        assert "Devon Walsh" in result.answer
    finally:
        bus.close()
