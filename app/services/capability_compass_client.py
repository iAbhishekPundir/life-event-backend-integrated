"""
Capability Compass integration.

Wealth Client Prospecting is configured in a separate app (Capability
Compass, owned by another team). Admins there add/remove subprocesses --
Event Detection, Personalised Recommendations, Advisor Insights, Client
Sentiment, Workflow Orchestration -- and whatever is currently configured
is exactly what this app should show as workflow steps.

Compass's response is a generic capability/process/subprocess catalog, not
something purpose-built for this. The only reliable link back to our own
`workflow_steps` rows is matching `subprocess.name` against our `title`
column -- there is no shared slug or id between the two systems.
"""
import logging
from typing import Optional, Set

import requests

from app.config import settings

logger = logging.getLogger(__name__)


def get_active_subprocess_names() -> Optional[Set[str]]:
    """
    Returns the set of subprocess names currently configured under Wealth
    Client Prospecting in Capability Compass, or None if Compass could not
    be reached in time -- callers should treat None as "unavailable" and
    fail open (show all steps) rather than as "nothing is configured".
    """
    if not settings.compass_api_url:
        return None

    try:
        response = requests.get(
            settings.compass_api_url,
            timeout=settings.compass_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.warning(
            "Capability Compass unreachable (%s) - showing all workflow steps unfiltered.",
            exc,
        )
        return None

    names: Set[str] = set()
    for process in data.get("processes", []) or []:
        for subprocess in process.get("subprocesses", []) or []:
            name = (subprocess.get("name") or "").strip()
            if name:
                names.add(name)

    if not names:
        logger.warning(
            "Capability Compass returned no subprocesses - showing all workflow steps unfiltered."
        )
        return None

    return names
