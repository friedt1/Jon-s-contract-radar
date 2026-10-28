"""Parse individually identified NYSCR notices from an authorized text export.

This module NEVER logs in, crawls NYSCR, or claims an open bid without its
original detail URL and an independently confirmed status.
"""
import datetime as dt
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

LABELS = ("Agency", "Division", "Issue date", "Due date", "Location", "Category", "Ad type", "Description", "Detail URL", "Solicitation URL")
WORK = re.compile(
    r"tree (?:removal|trimming|pruning|clearing|cutting|service|maintenance)|"
    r"remov(?:al|e) of (?:hazardous )?trees?|"
    r"stump (?:removal|grinding)|brush (?:clearing|removal|cutting)|"
    r"vegetation management|right.of.way (?:clearing|vegetation)|"
    r"line clearance|roadside clearing|land clearing|forestry mulching|"
    r"storm (?:debris|cleanup)|disaster debris", re.I
)
NUMBER = re.compile(r"^\d{6,9}$")
DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")


def extract(text):
    """Yield record dictionaries; distinct CR numbers are record boundaries.

    Source text may be a user-authorized export of the public listing view.
    This extracts *candidates*, not confirmed open solicitations.
    """
    lines = [s.strip() for s in text.splitlines() if s.strip()]
    result, seen = [], set()
    # A CR number follows a title and literal CR#: label in NYSCR's listing.
    markers = [i for i in range(1, len(lines)-1)
               if lines[i] == "CR#:" and NUMBER.fullmatch(lines[i+1])]
    label_pattern = re.compile(r"^(" + "|".join(re.escape(label) for label in LABELS) + r"):\s*(.*)$", re.I)
    for n, marker in enumerate(markers):
        number = lines[marker+1]
        if number in seen or marker == 0:
            continue
        seen.add(number)
        start = marker + 2
        stop = markers[n+1]-1 if n+1 < len(markers) else len(lines)
        fields = {}
        for i in range(start, stop):
            match = label_pattern.fullmatch(lines[i])
            if not match:
                continue
            label = next(name for name in LABELS if name.lower() == match.group(1).lower())
            # Support both "Agency: Example" and the line-separated export format.
            value = match.group(2).strip()
            if label == "Description":
                # Authorized text exports may wrap the actual work scope onto
                # multiple lines. Stop at the next labeled field or CR boundary.
                continuation = []
                for next_line in lines[i+1:stop]:
                    if label_pattern.fullmatch(next_line):
                        break
                    continuation.append(next_line)
                value = " ".join([value] + continuation).strip()[:2000]
            elif not value and i + 1 < stop and not label_pattern.fullmatch(lines[i+1]):
                value = lines[i+1]
            fields[label] = value
        title = lines[marker-1]
        scope = fields.get("Description") or title
        if not WORK.search(title + " " + scope):
            continue
        link = fields.get("Detail URL") or fields.get("Solicitation URL") or ""
        parsed = urlparse(link)
        if (parsed.scheme != "https" or parsed.hostname not in ("nyscr.ny.gov", "www.nyscr.ny.gov")
                or not re.search(r"(?<!\d)" + re.escape(number) + r"(?!\d)", parsed.path + "?" + parsed.query)):
            link = ""
        due = fields.get("Due date", "")
        try:
            due_iso = dt.datetime.strptime(due, "%m/%d/%Y").date().isoformat() if DATE.fullmatch(due) else ""
        except ValueError:
            due_iso = ""
        result.append({
            "cr_number": number, "title": title,
            "agency": fields.get("Agency", ""),
            "location": fields.get("Location", ""),
            "deadline": due_iso,
            "category": fields.get("Category", ""),
            "source": "NYS Contract Reporter",
            "status": "research_only",
            "open_status": "unknown",
            "scope": scope,
            "deadline_time": "",
            "deadline_timezone": "unverified",
            "location_verified": False,
            "detail_url": link or None,
            "verification": "Authorized export only; original notice status, access permission, and worksite not independently verified",
        })
    return result


def promotable(notice, *, today=None):
    """Fail closed: only independently verified, unexpired official NYSCR notices.

    A listing/export alone is never sufficient. This function does not fetch
    the notice or grant access. The caller must independently establish the
    original official URL, authorization, live open status and worksite.
    """
    if not isinstance(notice, dict):
        return False
    today = today or dt.datetime.now(ZoneInfo("America/New_York")).date()
    link = notice.get("detail_url") or ""
    parsed = urlparse(link)
    number = str(notice.get("cr_number") or "")
    due = notice.get("deadline") or ""
    try:
        due_date = dt.date.fromisoformat(due)
    except (ValueError, TypeError):
        return False
    if not NUMBER.fullmatch(number) or due_date < today:
        return False
    if parsed.scheme != "https" or parsed.hostname not in ("nyscr.ny.gov", "www.nyscr.ny.gov"):
        return False
    # A generic portal homepage is not an original solicitation.
    if not re.search(r"(?<!\d)" + re.escape(number) + r"(?!\d)", parsed.path + "?" + parsed.query):
        return False
    return bool(
        notice.get("status") == "verified_open"
        and notice.get("authorized_access") is True
        and notice.get("open_status_confirmed") is True
        and notice.get("location_confirmed") is True
        and notice.get("agency")
        and notice.get("location")
        and WORK.search(str(notice.get("scope") or notice.get("title") or ""))
    )
