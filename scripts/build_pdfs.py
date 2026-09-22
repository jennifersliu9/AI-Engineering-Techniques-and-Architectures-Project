"""Generate Harborline companion PDFs with the standard library only."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(pages: list[list[tuple[str, int, int]]]) -> bytes:
    """pages: list of pages; each page is a list of (text, x, y) in 12-pt Helvetica."""
    objects: list[bytes] = []

    def add(obj: str | bytes) -> int:
        if isinstance(obj, str):
            obj = obj.encode("latin-1", "replace")
        objects.append(obj)
        return len(objects)

    # Placeholder; real objects start at 1 after we build content.
    page_content_ids: list[int] = []
    page_obj_ids: list[int] = []

    content_streams: list[str] = []
    for page in pages:
        commands = ["BT", "/F1 11 Tf"]
        last_y = None
        for text, x, y in page:
            safe = pdf_escape(text)
            if last_y is None:
                commands.append(f"1 0 0 1 {x} {y} Tm ({safe}) Tj")
            else:
                commands.append(f"1 0 0 1 {x} {y} Tm ({safe}) Tj")
            last_y = y
        commands.append("ET")
        stream = "\n".join(commands)
        content_streams.append(stream)

    # Object 1: catalog
    # We assign IDs after we know counts.
    # Layout:
    # 1 catalog
    # 2 pages
    # 3 font
    # 4..3+N content
    # then page objects
    n = len(pages)
    catalog_id = 1
    pages_id = 2
    font_id = 3
    first_content = 4
    first_page = 4 + n

    for i, stream in enumerate(content_streams):
        page_content_ids.append(first_content + i)
    for i in range(n):
        page_obj_ids.append(first_page + i)

    kids = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objs: dict[int, bytes] = {}
    objs[catalog_id] = f"1 0 obj\n<< /Type /Catalog /Pages {pages_id} 0 R >>\nendobj\n".encode()
    objs[pages_id] = (
        f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {n} >>\nendobj\n".encode()
    )
    objs[font_id] = (
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    for cid, stream in zip(page_content_ids, content_streams):
        data = stream.encode("latin-1", "replace")
        objs[cid] = (
            f"{cid} 0 obj\n<< /Length {len(data)} >>\nstream\n".encode()
            + data
            + b"\nendstream\nendobj\n"
        )

    for pid, cid in zip(page_obj_ids, page_content_ids):
        objs[pid] = (
            f"{pid} 0 obj\n"
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Contents {cid} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>\n"
            f"endobj\n"
        ).encode()

    max_id = first_page + n - 1
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i in range(1, max_id + 1):
        offsets.append(len(out))
        out.extend(objs[i])
    xref_pos = len(out)
    out.extend(f"xref\n0 {max_id + 1}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for i in range(1, max_id + 1):
        out.extend(f"{offsets[i]:010d} 00000 n \n".encode())
    out.extend(
        f"trailer\n<< /Size {max_id + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode()
    )
    return bytes(out)


def wrap(text: str, width: int = 92) -> list[str]:
    lines: list[str] = []
    for raw in text.split("\n"):
        if raw == "":
            lines.append("")
            continue
        if raw.startswith("  "):
            indent = raw[: len(raw) - len(raw.lstrip(" "))]
            body = raw.strip()
            chunk_w = width - len(indent)
            while len(body) > chunk_w:
                cut = body.rfind(" ", 0, chunk_w)
                if cut < 20:
                    cut = chunk_w
                lines.append(indent + body[:cut])
                body = body[cut:].lstrip()
            lines.append(indent + body)
            continue
        words = raw.split()
        current = ""
        for word in words:
            trial = word if not current else current + " " + word
            if len(trial) > width:
                if current:
                    lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
    return lines


def page_from_lines(lines: list[str], title: str | None = None) -> list[tuple[str, int, int]]:
    items: list[tuple[str, int, int]] = []
    y = 742
    if title:
        items.append((title, 48, y))
        y -= 22
    for line in lines:
        if y < 48:
            break
        items.append((line, 48, y))
        y -= 13
    return items


def paginate(paragraphs: str, header: str, footer: str) -> list[list[tuple[str, int, int]]]:
    lines = wrap(paragraphs, 92)
    pages: list[list[tuple[str, int, int]]] = []
    usable = 48  # lines per page after header/footer
    chunks: list[list[str]] = []
    buf: list[str] = []
    for line in lines:
        buf.append(line)
        if len(buf) >= usable:
            chunks.append(buf)
            buf = []
    if buf:
        chunks.append(buf)
    total = len(chunks) or 1
    if not chunks:
        chunks = [[]]
    for i, chunk in enumerate(chunks, start=1):
        page_lines = [header, ""] + chunk + ["", f"{footer}  |  Page {i} of {total}"]
        pages.append(page_from_lines(page_lines))
    return pages


EXPENSE = """HARBORLINE TECHNOLOGIES, INC.
2026 TRAVEL AND EXPENSE LIMITS
Policy companion POL-EXP-004-LIM  |  Controlling policy: POL-EXP-004
Effective 1 January 2026  |  Revised 1 September 2026
Finance Operations  |  travel@harborline.example  |  Voyage + HarborTravel

If a manager quotes a different number in Slack, this sheet and POL-EXP-004 win
unless the VP of Finance approved a HarborHub exception.

AIR, RAIL, AND CAR
- Book the lowest logical economy fare within two hours of requested arrival.
- Extra-legroom seats: allowed on flights of 4+ hours, up to $75 each way.
- Premium economy: 6+ hour flights with director approval.
- Business class: CFO only (typically 10+ hours or documented medical need).
- Book 14 days ahead domestic, 21 days international.
- Rail preferred for Bos-NY-DC, Dublin regional, and Seattle-Portland when close.
- Rental: midsize or smaller. CDW waiver off in the US on the corporate card; on abroad.
- Personal-car mileage: current IRS rate (US) or Revenue rate (Ireland). No commuting.

HOTELS (room + mandatory tax / night)
- US general: $225
- NYC, San Francisco, Washington DC, Boston: $325
- International general: $280
- London, Zurich, Tokyo, Singapore: $380
- Airbnb allowed for 7+ nights when cheaper and Security has no objection.

MEALS (actuals, not a cash per diem)
- US travel: $75 per calendar day at destination
- International travel: $100 per calendar day
- Day trip, no hotel: $40 (lunch; dinner only if you return after 8:00 p.m.)
- Working lunch in a hub city, no travel: $25 per person
- Alcohol: max 2 drinks with a meal; no bar tab without food
- Tips: up to 20% US or local custom, inside the cap

RECEIPTS AND TIMING
- Receipt REQUIRED at $25 and above. Itemized meals at $25+.
- Missing-receipt affidavits: 2 per employee per quarter.
- Submit Voyage within 15 calendar days of the expense or trip return.
- Reports older than 60 days need director approval and may be denied.
- Year-end: late-December spend in Voyage by 15 January.

CUSTOMER ENTERTAINMENT
- $150 per person including tax and tip unless VP Sales or VP CS pre-approves
- Customer gifts: $75 fair-market value per person per year; no cash; gift cards max $25
- Government / public-sector customers: follow the STRICTER of this sheet and their rules
- Adult entertainment, gambling, political fundraisers: never

CORPORATE CARD
- Directors+, frequent travelers (6+ nights/quarter): card issued
- No personal charges. Accidental personal use repaid in 15 days.
- Cash withdrawal only in a documented emergency; HarborHub case in 48 hours
- Late coding twice in a year can suspend the card

NOT REIMBURSABLE (highlights)
Airline club memberships (except a delay day-pass), companion travel, commuting,
childcare, pet boarding, traffic tickets, minibar, spa, clothing, home internet
beyond the $50 stipend in POL-RMT-003, furniture beyond the $500 setup stipend,
and equipment (that is POL-EQP-008 / IT, not Voyage).

PERSONAL DAYS TACKED ON
Book the business itinerary first. You pay fare difference and hotel/meals on
personal days. International add-on days still count toward POL-RMT-003.

EXCEPTIONS
Under published cap: manager. Over cap: VP of Finance. Over $2,500: CFO.
A Slack thumbs-up is not an exception.
"""

SECURITY = """HARBORLINE TECHNOLOGIES, INC.
INFORMATION SECURITY SUMMARY (NEW-HIRE PACKET)
Policy companion POL-SEC-005-SUM  |  Controlling policy: POL-SEC-005
Also read: acceptable-use-policy.txt (POL-SEC-005-AUP)
Effective 1 January 2026  |  Revised 1 September 2026
Security 24/7: +1-206-555-0199  |  security@harborline.example
Phishing: phishing@harborline.example

WHY THIS SHEET EXISTS
Harborline hosts operational data for logistics, field-service, and wholesale
customers. This one-pager is what goes in the week-one packet. It does not
replace POL-SEC-005. Production and customer access stay blocked until you
finish the 90-minute Harborline Learn security module (POL-ONB-007).

DATA CLASSES
- Public: marketing site, published blogs, job ads. Share freely.
- Internal: org charts, this policy set, ordinary Slack. Employees and signed contractors.
- Confidential: compensation, home addresses, unpublished roadmaps, CRM names.
  Named access on Company systems only. No personal email.
- Restricted: production customer data, credentials, payment data, production
  logs with payloads, government IDs. Production VPC / approved admin tools only.
When unsure, use the higher class. Screenshots inherit the source class.
Restricted exports expire in 30 days. Delete them when the ticket closes.

IDENTITY
Okta + MFA on every internet-facing app. Preferred MFA is a hardware key for
admins, otherwise Okta Verify. SMS MFA is a 7-day recovery method only.
1Password is the password manager. Unique 16+ character passwords when SSO is
impossible. Never paste a password into Slack.

DEVICES
Company laptop only (POL-EQP-008). Full-disk encryption, 5-minute screen lock,
EDR agent stays installed. No BYOD laptops. Personal phones: work profile for
Slack / MFA / email only; no production VPN. USB blocked unless Security
approved. Lost or stolen: call +1-206-555-0199 immediately.

WHERE YOU MAY WORK
Hub Wi-Fi or home office on WPA2/WPA3. VPN required for production, payroll,
and Restricted systems. Cafe / coworking: Internal and Public work only. Never
admin production or open payroll from a shared table (POL-RMT-003).

AI TOOLS
Use the approved internal assistant for Internal material. Do NOT paste
Confidential people data, Restricted customer data, credentials, or unpublished
security findings into ChatGPT, Claude.ai, Gemini, consumer Copilot, or other
public models. Customer contracts that forbid AI-assisted work win.

INCIDENTS — ONE HOUR
Call +1-206-555-0199 if it is active (session still open, laptop still missing,
ransomware note). Email security@harborline.example with what, when, which
systems, and whether a customer might be affected. Do not power off unless
told (except disconnect Wi-Fi for ransomware). Do not brief customers until
Security and Communications agree. Good-faith false alarms are encouraged.

PHISHING
Report Phish button or phishing@harborline.example. Finance will never change
a vendor bank account by Slack alone.

PHYSICAL
No tailgating. Shred Confidential paper. Wipe street-facing whiteboards.
Report a lost badge the same day.

VENDORS
No shadow vendors on a personal card for customer data. Contracts + DPA when
Confidential or Restricted data is involved.

EXCEPTIONS
Only the Head of Information Security (or delegate) can approve USB, SMS MFA
beyond 7 days, personal-device production access, or a public-AI use case.
Exceptions expire. Slack is not an approval record.

LEAVE / LAST DAY
Confidentiality survives employment. Return keys, badge, YubiKey, and laptop
within 10 days (POL-EQP-008). Do not self-wipe the disk.
"""


def main() -> None:
    CORPUS.mkdir(parents=True, exist_ok=True)
    expense_pdf = build_pdf(
        paginate(
            EXPENSE,
            "Harborline  |  POL-EXP-004-LIM  |  2026 Expense Limits",
            "Fictional company job aid. Not a substitute for POL-EXP-004.",
        )
    )
    (CORPUS / "expense-limits-2026.pdf").write_bytes(expense_pdf)

    security_pdf = build_pdf(
        paginate(
            SECURITY,
            "Harborline  |  POL-SEC-005-SUM  |  Security summary",
            "Fictional company job aid. Not a substitute for POL-SEC-005.",
        )
    )
    (CORPUS / "information-security-summary.pdf").write_bytes(security_pdf)
    print("Wrote", CORPUS / "expense-limits-2026.pdf", len(expense_pdf), "bytes")
    print("Wrote", CORPUS / "information-security-summary.pdf", len(security_pdf), "bytes")


if __name__ == "__main__":
    main()
