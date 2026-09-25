# Harborline evaluation report

n=26  seed=42  transport=mcp-inproc
families={'policy_qa': 8, 'multi_doc': 4, 'tool': 8, 'ambiguous': 3, 'oos': 3}

Gold tasks: `eval/eval_tasks.json` (26 items). Runner: `python -m harborline.cli report --backend tfidf --write`.
Answer mode is retrieve + rule-based agent (no LLM synthesis). Groundedness counts a task as grounded if it cites a gold source, matches a gold phrase, or correctly refuses/clarifies.
Partial match is the stricter check against `expected_contains`. Citation accuracy is recall of gold source filenames among returned citations.

## Answer quality
- groundedness: 1.0
- citation accuracy (recall of gold sources): 0.9375
- citation precision: 0.3679
- partial match vs gold phrases: 0.7308

## Agent behavior
- tool selection accuracy: 1.0
- workflow completion rate: 0.9231
- escalation / clarification accuracy: 0.9231
- action-safety pass rate: 1.0

## System latency (local, in-process MCP)
- n=16  p50=145.1202 ms  p95=394.0733 ms
- cold (first timed task)=637.27 ms
- warm p50=131.5898 ms  warm p95=259.1856 ms
- Local in-process MCP. Free-tier hosts that sleep after inactivity add extra cold-start time on the first HTTP request (often 30-90s) that is not in these numbers.

## Ablation
- retrieval recall by top_k: {'3': 0.875, '5': 0.9792, '8': 1.0}
- tool availability: {'agent_with_mcp_tools_partial_match': 1.0, 'retrieve_only_no_tools_partial_match': 0.375, 'n': 8, 'note': 'Same tool-family tasks: MCP agent vs harborline.answer.ask retrieve-only.'}

## Gold set (question -> gold answer)
- **t-pto-tenure** [policy_qa] How many PTO days do I get after my second anniversary?
  - gold: 20 days (160 hours) after the second anniversary (POL-PTO-001).
  - [FAIL] grounded=True partial=False cite_recall=1.0 tools=['search_policy_documents'] 637.27ms
- **t-pto-carryover** [policy_qa] What is the PTO carryover cap in hours?
  - gold: 40 hours carryover cap except California (POL-PTO-001).
  - [FAIL] grounded=True partial=False cite_recall=1.0 tools=['search_policy_documents'] 191.22ms
- **t-hotel-cap** [policy_qa] What is the US hotel nightly cap for a Chicago trip?
  - gold: US hotel cap is $225 per night (POL-EXP-004).
  - [PASS] grounded=True partial=False cite_recall=1.0 tools=['check_policy_compliance'] 217.34ms
- **t-receipt** [policy_qa] Do I need a receipt for an 18 dollar lunch?
  - gold: Receipts are required at $25 and above (POL-EXP-004).
  - [PASS] grounded=True partial=False cite_recall=1.0 tools=['check_policy_compliance'] 205.71ms
- **t-401k-vest** [policy_qa] When does the Harborline 401k match vest?
  - gold: Company 401(k) match vests immediately (POL-BEN-006).
  - [PASS] grounded=True partial=True cite_recall=1.0 tools=['search_policy_documents'] 235.47ms
- **t-parental-secondary** [policy_qa] How many weeks of paid parental leave do secondary caregivers get?
  - gold: 8 weeks paid for secondary caregivers (POL-FAM-011).
  - [PASS] grounded=True partial=False cite_recall=1.0 tools=['search_policy_documents'] 238.59ms
- **t-thanksgiving-holiday** [policy_qa] Is the day after Thanksgiving a company holiday in 2026?
  - gold: Yes. 27 November 2026 is a US company holiday.
  - [PASS] grounded=True partial=False cite_recall=1.0 tools=['search_policy_documents'] 190.57ms
- **t-remote-radius-policy** [policy_qa] What is the mile radius that separates hub and remote employees?
  - gold: Hub vs remote uses a 50-mile rule (POL-RMT-003).
  - [PASS] grounded=True partial=True cite_recall=0.0 tools=[] 28.44ms
- **t-multi-thanksgiving-hub** [multi_doc] I live 32 miles from the Seattle office and want PTO Wednesday through Friday of Thanksgiving week 2026. Do I lose PTO hours for the company holidays, and do I still owe three office days that week?
  - gold: Thanksgiving and the day after are holidays (no PTO charged). Hub staff still follow POL-RMT-003 office-day rules unless the office is closed. The live agent should clarify because the ask spans PTO and office-day workflows.
  - [PASS] grounded=True partial=True cite_recall=None tools=[] 10.26ms
- **t-multi-newhire-benefits** [multi_doc] How long do I have to elect medical coverage after my start date?
  - gold: 30 days from start date to elect medical (POL-BEN-006 / POL-ONB-007).
  - [PASS] grounded=True partial=False cite_recall=1.0 tools=['search_policy_documents'] 236.12ms
- **t-multi-phishing** [multi_doc] What do I do if I clicked a phishing link and entered my Okta password?
  - gold: Report immediately; Security hotline +1-206-555-0199 (POL-SEC-005).
  - [PASS] grounded=True partial=True cite_recall=1.0 tools=['search_policy_documents'] 154.32ms
- **t-multi-onboarding-i9** [multi_doc] What must a new hire complete on day one besides I-9?
  - gold: Day-one checklist in POL-ONB-007 includes I-9, HarborHub access, and security training gates.
  - [PASS] grounded=True partial=True cite_recall=1.0 tools=['get_policy_section'] 131.59ms
- **t-tool-remote-1008** [tool] Am I eligible for fully remote work living in Tacoma?
  - gold: Alex Kim is hub_seattle at 32 miles; hub staff owe 3 office days. Fully remote needs People Ops reclass (POL-RMT-003).
  - [PASS] grounded=True partial=True cite_recall=1.0 tools=['lookup_employee_profile', 'search_policy_documents', 'check_policy_compliance'] 313.01ms
- **t-tool-pto-1014** [tool] Can I take PTO next week?
  - gold: Devon Walsh has 5.0 PTO hours and eligible_to_use=false until 2026-10-08.
  - [PASS] grounded=True partial=True cite_recall=1.0 tools=['lookup_employee_profile', 'check_pto_balance', 'get_policy_section'] 99.49ms
- **t-tool-submit-pto** [tool] Please submit a PTO request for next Friday
  - gold: No live HarborHub write. MOCK ticket pending confirmation.
  - [PASS] grounded=True partial=True cite_recall=None tools=['lookup_employee_profile', 'check_pto_balance', 'get_policy_section', 'create_mock_hr_ticket'] 81.65ms
- **t-tool-benefits-1008** [tool] What medical plan and 401k deferral do I have?
  - gold: Look up EMP-1008 HarborHub benefits elections (POL-BEN-006).
  - [PASS] grounded=True partial=True cite_recall=1.0 tools=['search_policy_documents', 'lookup_benefits_status'] 130.39ms
- **t-tool-intern-pto** [tool] Can I take PTO next Friday?
  - gold: Maya Chen is an intern and does not accrue PTO (POL-PTO-001).
  - [PASS] grounded=True partial=True cite_recall=None tools=['lookup_employee_profile', 'check_pto_balance', 'get_policy_section'] 91.11ms
- **t-tool-triage-hotline** [tool] I need to file a case about harassment. What is the hotline?
  - gold: Report to manager, hr@harborline.example, or +1-800-555-0148. Ticket/email stay MOCK.
  - [PASS] grounded=True partial=True cite_recall=1.0 tools=['search_policy_documents', 'create_mock_hr_ticket', 'draft_hr_email'] 158.65ms
- **t-tool-hotel-over-cap** [tool] Can I expense a $250 hotel night in Chicago?
  - gold: Noncompliant: US hotel cap is $225 (POL-EXP-004).
  - [PASS] grounded=True partial=True cite_recall=1.0 tools=['check_policy_compliance'] 166.01ms
- **t-ambiguous-remote-pto** [ambiguous] remote PTO hybrid vacation
  - gold: Clarify which workflow: remote eligibility vs PTO guidance.
  - [PASS] grounded=True partial=True cite_recall=None tools=[] 12.29ms
- **t-ambiguous-benefits-hub** [ambiguous] I have a question about 401k enrollment and also my hub office days
  - gold: Matches benefits and remote workflows; ask the user to pick one.
  - [PASS] grounded=True partial=True cite_recall=None tools=[] 11.66ms
- **t-clarify-remote-no-id** [ambiguous] Am I eligible for remote work?
  - gold: Need an employee id such as EMP-1008 before applying the 50-mile hub rule.
  - [PASS] grounded=True partial=True cite_recall=None tools=[] 12.45ms
- **t-oos-bitcoin** [oos] Should I buy bitcoin with my bonus?
  - gold: Out of corpus. Refuse; do not invent an answer.
  - [PASS] grounded=True partial=True cite_recall=None tools=[] 14.61ms
- **t-oos-vote** [oos] Who should I vote for in the next election?
  - gold: Out of corpus. Refuse.
  - [PASS] grounded=True partial=True cite_recall=None tools=[] 15.2ms
- **t-oos-other-employer** [oos] How does Acme Corp handle bonuses versus Harborline?
  - gold: Other-employer policies are out of corpus. Refuse.
  - [PASS] grounded=True partial=True cite_recall=None tools=[] 14.3ms
- **t-missing-employee** [tool] Am I remote eligible?
  - gold: No HarborHub profile for EMP-9999. Escalate; do not invent eligibility.
  - [PASS] grounded=True partial=True cite_recall=None tools=['lookup_employee_profile'] 21.19ms
