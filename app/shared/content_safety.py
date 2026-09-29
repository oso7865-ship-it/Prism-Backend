"""Shared secret-suspect filter; not a complete DLP system."""

import re

SECRET = re.compile(
    "-----BEGIN [A-Z ]*PRIVATE KEY|(?:gh[pousr]_[A-Za-z0-9]{15,}|"
    "github_pat_[A-Za-z0-9_]{15,}|sk-[A-Za-z0-9_-]{12,}|AKIA[A-Z0"
    "-9]{16})|(?:password|secret|api[_-]?key|token)\\s*[:=]\\s*[\\\"'"
    "][^\\\"'\\r\\n]{4,}[\\\"']",
    re.I,
)
