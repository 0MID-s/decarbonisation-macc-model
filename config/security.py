"""Security helpers shared by the lint, the write wrapper and the scanner."""
from typing import FrozenSet, Tuple
from urllib.parse import urlsplit

# Official / reputable publisher domains only (CLAUDE.md security constraint).
# Add-domain procedure: adding a host is a deliberate reviewed change in its
# own commit and requires a one-line justification row in the docs/SECURITY.md
# "Allowed source domains" table. Never broaden an entry to make a URL pass.
ALLOWED_DOMAINS = (
    "aib-net.org", "eex.com", "efrag.org", "ember-energy.org", "ens.dk",
    "europa.eu", "gov.uk", "ifrs.org", "iiasa.ac.at", "ngfs.net", "pbl.nl",
    "rvo.nl", "stern.nyu.edu", "theicct.org",
)  # type: Tuple[str, ...]


def host_allowed(url):
    """True iff url is https and its parsed hostname is on the allowlist."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    if parts.scheme != "https" or not host:
        return False
    if not all(ord(c) < 128 for c in host):
        return False
    if any(label.startswith("xn--") for label in host.split(".")):
        return False
    return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)


INJECTION_PREFIXES = ("=", "+", "-", "@")
BAD_LEADING_CHARS = ("\t", "\r")


def is_injection_string(s):
    """True if text could be interpreted as a formula by a spreadsheet."""
    return s[:1] in BAD_LEADING_CHARS or s.lstrip()[:1] in INJECTION_PREFIXES


BANNED_FUNCTIONS = frozenset([
    "OFFSET", "INDIRECT", "LAMBDA", "LET", "XLOOKUP", "XMATCH", "FILTER",
    "SORT", "SORTBY", "UNIQUE", "SEQUENCE", "RANDARRAY", "TEXTSPLIT",
    "VSTACK", "HSTACK", "TAKE", "DROP", "CHOOSECOLS", "CHOOSEROWS", "TOCOL",
    "TOROW", "WRAPCOLS", "WRAPROWS", "EXPAND", "MAP", "REDUCE", "SCAN",
    "BYROW", "BYCOL", "MAKEARRAY", "NOW", "TODAY", "RAND", "RANDBETWEEN",
    "WEBSERVICE", "FILTERXML", "RTD", "CALL", "REGISTER", "REGISTER.ID",
    "EXEC", "HYPERLINK", "DDE", "INFO", "CELL",
])  # type: FrozenSet[str]

ALLOWED_NUMERIC_LITERALS = (0.0, 1.0)  # D-15
