"""Parse individually identified NYSCR notices from an authorized text export.

This module NEVER logs in, crawls NYSCR, or claims an open bid without its
original detail URL and an independently confirmed status.
"""
import datetime as dt
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

LABELS = ("Agency", "Division", "Issue date", "Due date", "Location", "Category", "Ad type")
WORK = re.compile(
    r"tree (?:removal|trimming|pruning|clearing|cutting|service|maintenance)|"
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
    for n, marker in enumerate(markers):
        number = lines[marker+1]
        if number in seen or marker == 0:
            continue
        seen.add(number)
        start = marker + 2
        stop = markers[n+1]-1 if n+1 < len(markers) else len(lines)
        fields = {}
        for i in range(start, max(start, stop-1)):
            name = lines[i].removesuffix(":")
            if name in LABELS and lines[i].endswith(":"):
                fields[name] = lines[i+1] if i+1 < stop else ""
        title = lines[marker-1]
        if not WORK.search(title):
            continue
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
            "scope": title,
            "deadline_time": "",
            "deadline_timezone": "unverified",
            "location_verified": False,
            "detail_url": None,
            "verification": "Original notice, access permission, active status, and work location not verified",
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
    if not re.search(r"(?<!\\d)" + re.escape(number) + r"(?!\\d)", parsed.path + "?" + parsed.query):
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
