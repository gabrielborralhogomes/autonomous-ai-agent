"""
AI Automation Agent — Illustrative Usage Example
=================================================
This file demonstrates the agent's public interface concept.
The actual implementation is proprietary.
"""

import asyncio


# ── Example 1: Simple web scraping objective ──────────────────────────────────

OBJECTIVE_WEB = """
Go to the company intranet portal, log in, navigate to the pending approvals
section, extract all pending items with their deadlines, and save the result
to a file named 'pending_approvals.xlsx'.
"""


# ── Example 2: End-to-end report + email objective ───────────────────────────

OBJECTIVE_REPORT = """
Open the ERP system, generate the monthly sales report for the current month,
download the Excel file, calculate the total revenue per region,
and send the summary to the finance team at finance@company.com.
"""


# ── Example 3: Document processing objective ─────────────────────────────────

OBJECTIVE_DOCS = """
Read all PDF invoices in the 'invoices/' folder, extract supplier name,
invoice number, and total amount from each one, consolidate into a single
spreadsheet, and flag any invoice with amount above $10,000.
"""


# ── How the agent would be invoked (interface illustration) ───────────────────

async def run_agent(objective: str, mode: str = "plan_execute") -> dict:
    """
    Illustrative interface — actual implementation is proprietary.

    Args:
        objective: Plain-language task description.
        mode: 'plan_execute' (1 LLM call + deterministic exec)
              or 'orchestrate' (reactive, N LLM calls).

    Returns:
        {
            "success": bool,
            "message": str,          # final answer or error description
            "token_usage": {...},    # API cost breakdown
            "memory": {...},         # relevant data collected during execution
        }
    """
    # provider and registry setup happens internally
    # agent selects tools, executes steps, recovers from errors automatically
    ...


# ── Record & Replay illustration ─────────────────────────────────────────────

"""
First run:  agent calls the LLM, records every successful step to plans/<hash>.json
            Output: plans/a3f9c1d84b2e.json

Second run: agent detects the saved plan, replays all steps with zero API cost
            Output: same result, $0.00 cost
"""


# ── Tool categories available to the agent ───────────────────────────────────

AVAILABLE_TOOLS = {
    "web":         ["navigate", "click", "fill", "select", "download", "screenshot"],
    "email":       ["read_inbox", "send_email", "search", "mark_read"],
    "file":        ["read", "write", "list", "move", "archive", "extract_zip"],
    "spreadsheet": ["read_sheet", "write_sheet", "create_workbook", "merge"],
    "document":    ["extract_text", "regex_find", "parse_table", "convert"],
    "windows":     ["open_app", "click_window", "type_text", "press_key"],
    "api":         ["get", "post", "put", "delete", "authenticate"],
    "data":        ["filter", "aggregate", "join", "transform", "sort"],
    "memory":      ["store", "retrieve", "list_keys", "delete"],
    "visual":      ["screenshot", "analyze_image", "verify_state"],
}


if __name__ == "__main__":
    asyncio.run(run_agent(OBJECTIVE_WEB, mode="plan_execute"))
