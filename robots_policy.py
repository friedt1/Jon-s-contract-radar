"""Conservative robots.txt access guard for public procurement scans.

No login bypass, no silent assumption that a reachable page permits crawling.
Unknown policy (timeouts, 5xx, malformed URLs) fails closed. HTTP 404/410
means no robots policy is published, per robots conventions.
"""
import re
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.robotparser import RobotFileParser

from source_config import public_dns_hostname

USER_AGENT = "JonsContractRadar"
MAX_ROBOTS_BYTES = 250_000
# Reject encoded control bytes before even requesting the publisher's robots.txt.
_UNSAFE_ENCODED = re.compile(r"%(?:0[0-9a-f]|1[0-9a-f]|7f|5c)", re.I)
_CACHE = {}
_LOCK = Lock()


class RobotsDenied(PermissionError):
    """The requested path is disallowed or robots policy could not be verified."""

class _SameOriginRobotsRedirect(HTTPRedirectHandler):
    """Fail closed before a robots.txt redirect can reach another origin.

    A redirected policy must not silently authorize a different publisher.
    Redirects to login pages, non-robots paths, insecure URLs and ports are
    rejected without making the destination request.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            original, target = urlsplit(req.full_url), urlsplit(newurl)
            original_port = original.port or (443 if original.scheme == "https" else 80)
            target_port = target.port or (443 if target.scheme == "https" else 80)
            if (target.scheme != original.scheme
                    or not original.hostname or not target.hostname
                    or target.hostname != original.hostname
                    or target_port != original_port
                    or target.username is not None or target.password is not None
                    or target.path != "/robots.txt" or target.query or target.fragment):
                raise RobotsDenied("robots redirect blocked: different origin or policy path")
        except ValueError as error:
            raise RobotsDenied("robots redirect blocked: malformed destination") from error
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def urlopen(request, timeout):
    """Read robots policy with a per-request, redirect-restricted opener."""
    return build_opener(_SameOriginRobotsRedirect()).open(request, timeout=timeout)



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
    except RobotsDenied as error:
        return ("deny", str(error))
    except (URLError, OSError, TimeoutError, ValueError) as error:
        return ("deny", "robots policy unavailable: " + type(error).__name__)
    parser = RobotFileParser()
    parser.parse(body.decode("utf-8", "replace").splitlines())
    return ("parser", parser)


def allowed(url):
    # All callers, including redirects and newly discovered notice links,
    # must pass the public-host guard *before* requesting robots.txt. A
    # private/loopback address must not become reachable merely because its
    # robots policy is missing (HTTP 404/410 means allow for public hosts).
    if (not isinstance(url, str) or not url
            or any(ord(char) < 33 or ord(char) == 127 or char == "\\" for char in url)
            or _UNSAFE_ENCODED.search(url)):
        return False, "invalid public URL"
    try:
        parsed = urlsplit(url)
        expected_port = 443 if parsed.scheme == "https" else 80
        if (parsed.scheme not in ("https", "http") or not parsed.netloc
                or not public_dns_hostname(parsed.hostname)
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, expected_port)
                or parsed.fragment):
            return False, "invalid public URL"
    except ValueError:
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
