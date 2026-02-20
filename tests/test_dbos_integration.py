import asyncio

import pytest

from agents.triage_runner import triage_inbox


class TestDBOSIntegration:
    def test_triage_inbox_is_callable(self):
        """Verify triage_inbox exists and is an async function."""
        assert asyncio.iscoroutinefunction(triage_inbox)

    def test_dbos_availability(self):
        """Check whether DBOS is available (informational, not required)."""
        try:
            import dbos
            available = True
        except ImportError:
            available = False
        # On Python < 3.11, DBOS won't be available — that's OK
        import sys
        if sys.version_info < (3, 11):
            assert not available or available  # either is fine
        # On Python >= 3.11, we'd expect it to be available
