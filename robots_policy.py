"""Conservative robots.txt access guard for public procurement scans.

No login bypass, no silent assumption that a reachable page permits crawling.
Unknown policy (timeouts, 5xx, malformed URLs) fails closed. HTTP 404/410
means no robots policy is published, per robots conventions.
"""
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

USER_AGENT = "JonsContractRadar"
MAX_ROBOTS_BYTES = 250_000
_CACHE = {}
_LOCK = Lock()


class RobotsDenied(PermissionError):
    """The requested path is disallowed or robots policy could not be verified."""


def _policy(origin):
    request = Request(origin + "/robots.txt", headers={
        "User-Agent": "Mozilla/5.0 (compatible; JonsContractRadar/5.0; public listings)",
        "Accept": "text/plain,*/*;q=0.1",
    })
    try:
        with urlopen(request, timeout=5) as response:
            if response.status != 200:
                return ("deny", "robots HTTP " + str(response.status))
            body = response.read(MAX_ROBOTS_BYTES + 1)
            if len(body) > MAX_ROBOTS_BYTES:
                return ("deny", "robots policy too large")
    except HTTPError as error:
        if error.code in (404, 410):
            return ("allow", "robots policy absent")
        return ("deny", "robots HTTP " + str(error.code))
    except (URLError, OSError, TimeoutError, ValueError) as error:
        return ("deny", "robots policy unavailable: " + type(error).__name__)
    parser = RobotFileParser()
    parser.parse(body.decode("utf-8", "replace").splitlines())
    return ("parser", parser)


def allowed(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.username:
        return False, "invalid public URL"
    origin = parsed.scheme + "://" + parsed.netloc
    with _LOCK:
        policy = _CACHE.get(origin)
    if policy is None:
        loaded = _policy(origin)
        with _LOCK:
            policy = _CACHE.setdefault(origin, loaded)
    mode, value = policy
    if mode == "allow":
        return True, value
    if mode == "deny":
        return False, value
    if value.can_fetch(USER_AGENT, url):
        return True, "robots permits requested path"
    return False, "robots disallows requested path"


def assert_allowed(url):
    ok, reason = allowed(url)
    if not ok:
        raise RobotsDenied(reason)
