"""Harborline MCP server.

Transport default is stdio (Cursor and the CLI agent spawn this process).
Optional Streamable HTTP / SSE: `python -m harborline.mcp_server --transport streamable-http`.

Do not use `from __future__ import annotations` here: FastMCP 1.9 inspects
runtime type objects and breaks on postponed string annotations.
"""

import argparse

from harborline.tools import (
    check_policy_compliance,
    check_pto_balance,
    create_mock_hr_ticket,
    draft_hr_email,
    get_policy_section,
    lookup_benefits_status,
    lookup_employee_profile,
    search_policy_documents,
)

MCP_TOOL_NAMES = (
    "search_policy_documents",
    "get_policy_section",
    "lookup_employee_profile",
    "check_pto_balance",
    "lookup_benefits_status",
    "create_mock_hr_ticket",
    "draft_hr_email",
    "check_policy_compliance",
)


def create_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "harborline",
        log_level="WARNING",
        instructions=(
            "Fictional Harborline Technologies HR tools. "
            "search_policy_documents and get_policy_section read the RAG index. "
            "Employee/PTO/benefits tools read mock HarborHub JSON. "
            "create_mock_hr_ticket and draft_hr_email never write a live HRIS."
        ),
    )

    @mcp.tool(name="search_policy_documents")
    def search_policy_documents_tool(query: str, employee_id: str = "", kind: str = "") -> dict:
        """Search the Harborline RAG index for policy (and optional HarborHub) evidence."""
        return search_policy_documents(
            query,
            employee_id=employee_id or None,
            kind=kind or None,
        )

    @mcp.tool(name="get_policy_section")
    def get_policy_section_tool(policy_id: str, section: str = "") -> dict:
        """Return indexed chunks for a policy ID such as POL-PTO-001 and an optional heading."""
        return get_policy_section(policy_id, section=section)

    @mcp.tool(name="lookup_employee_profile")
    def lookup_employee_profile_tool(employee_id: str) -> dict:
        """Look up a fictional HarborHub profile (EMP-1xxx) from mock JSON."""
        return lookup_employee_profile(employee_id)

    @mcp.tool(name="check_pto_balance")
    def check_pto_balance_tool(employee_id: str) -> dict:
        """Return mock HarborHub PTO, sick, and floating-holiday balances."""
        return check_pto_balance(employee_id)

    @mcp.tool(name="lookup_benefits_status")
    def lookup_benefits_status_tool(employee_id: str) -> dict:
        """Return mock HarborHub medical/401k/stipend elections."""
        return lookup_benefits_status(employee_id)

    @mcp.tool(name="create_mock_hr_ticket")
    def create_mock_hr_ticket_tool(
        topic: str,
        summary: str,
        employee_id: str = "",
        confirm: bool = False,
    ) -> dict:
        """Draft an HR ticket. MOCK only. confirm=true keeps a session-only mock id."""
        return create_mock_hr_ticket(
            topic=topic,
            summary=summary,
            employee_id=employee_id or None,
            confirm=confirm,
        )

    @mcp.tool(name="draft_hr_email")
    def draft_hr_email_tool(
        employee_id: str,
        subject: str,
        body: str,
        confirm: bool = False,
    ) -> dict:
        """Draft an HR email. Never sent. confirm=true keeps a session-only MOCK."""
        return draft_hr_email(employee_id, subject, body, confirm=confirm)

    @mcp.tool(name="check_policy_compliance")
    def check_policy_compliance_tool(
        scenario: str,
        employee_id: str = "",
        policy_id: str = "",
    ) -> dict:
        """Compare a scenario to retrieved policy evidence and optional mock employee data."""
        return check_policy_compliance(
            scenario,
            employee_id=employee_id or None,
            policy_id=policy_id,
        )

    return mcp


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Harborline MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="stdio for Cursor/CLI; streamable-http or sse for a localhost service",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    mcp = create_server()
    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
