# Harborline mock structured data

Small fictional HarborHub-style JSON files that sit next to the [policy corpus](../corpus/README.md). Records share `employee_id` values and follow the same 2026 rules: PTO tenure bands, office locations, benefits elections, and ticket queues.

**As of:** 2026-09-21  
**Company:** Harborline Technologies, Inc.  
**Do not treat as real personal data.** Names, addresses, and ticket text are invented.

## Files

| File | Records | What it is for |
| --- | --- | --- |
| [offices.json](offices.json) | 3 | Seattle, Austin, and Dublin hubs (addresses match POL-RMT-003) |
| [employees.json](employees.json) | 16 | Profiles, manager chain, employment type, location category |
| [pto_balances.json](pto_balances.json) | 16 | PTO / sick / floating-holiday banks as of 21 Sep 2026 |
| [benefits_elections.json](benefits_elections.json) | 16 | Medical, dental, retirement, and stipend flags |
| [tickets.json](tickets.json) | 14 | IT, HR, security, finance, and workplace tickets |

Join everything on `employee_id` (for example `EMP-1008`). Offices join on `office_id`. Tickets may also reference `policy_id` from the corpus.

## People snapshot

| ID | Name | Role | Manager | Type | Location |
| --- | --- | --- | --- | --- | --- |
| EMP-1001 | Elena Voss | CEO | — | Full-time | Hub — Seattle |
| EMP-1002 | Marcus Hale | Chief People Officer | Elena | Full-time | Hub — Seattle |
| EMP-1003 | Priya Shah | Director, People Operations | Marcus | Full-time | Hub — Seattle |
| EMP-1004 | Jordan Ellis | HR Business Partner | Priya | Full-time | Hub — Austin |
| EMP-1005 | Niamh Byrne | Leave Administrator | Priya | Full-time | Hub — Dublin |
| EMP-1006 | David Okonkwo | CTO | Elena | Full-time | Hub — Seattle |
| EMP-1007 | Sofia Alvarez | Director of Engineering | David | Full-time | Remote — US (Berkeley, CA) |
| EMP-1008 | Alex Kim | Software Engineer | Sofia | Full-time | Hub — Seattle (Tacoma home) |
| EMP-1009 | Samira Haddad | Software Engineer | Sofia | Full-time | Hub — Austin |
| EMP-1010 | Liam O'Connell | Software Engineer | Sofia | Full-time | Remote — Ireland (Cork) |
| EMP-1011 | Chris Patel | Support Specialist | Sofia | Part-time 24h | Hub — Austin |
| EMP-1012 | Taylor Brooks | VP of Sales | Elena | Full-time | Hub — Austin |
| EMP-1013 | Riley Nguyen | Account Executive | Taylor | Full-time | Remote — US (Portland, OR) |
| EMP-1014 | Devon Walsh | Account Executive | Taylor | Full-time | Hub — Seattle (started 8 Sep 2026) |
| EMP-1015 | Amara Diallo | VP of Customer Success | Elena | Full-time | Hub — Seattle (parental leave) |
| EMP-1016 | Maya Chen | People intern | Priya | Intern | Hub — Seattle |

## Facts these rows are meant to exercise

- **Tenure bands (POL-PTO-001):** year-1 (Devon), year-2-to-3 transition (Alex), mid-tenure 20-day (Jordan, Samira), 25-day (Elena, David).
- **Proration:** Chris at 24 hours/week accrues `120 × 24/40` hours per year.
- **Interns:** Maya has no PTO and no 401(k).
- **New hire window:** Devon started 8 Sep 2026 — PTO not usable until 8 Oct; benefits election still open; medical starts 1 Oct.
- **California carryover:** Sofia’s PTO is not capped at 40 hours the way other US rows are.
- **Ireland:** Niamh and Liam use Irish holiday / sick schemes, not the US 10-day sick bank.
- **50-mile hub rule:** Alex lives in Tacoma (~32 miles) so remains Hub — Seattle.
- **Parental leave:** Amara is primary caregiver on POL-FAM-011 leave.
- **Tickets:** MFA lockout, phishing click, expense exception, PTO blackout, I-9, lost badge — each points at a policy ID.
