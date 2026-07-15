from __future__ import annotations

import os


RULESET_ID = "delivery-document-control"
RULESET_VERSION = "0.3.0"
APPLICATION_VERSION = "0.2.0"


def git_sha() -> str:
    return os.environ.get("RECON_GIT_SHA", "").strip()[:40]
