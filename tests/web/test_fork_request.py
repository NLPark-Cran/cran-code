"""Tests for the fork session request model (turn_index optional)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cran_code.web.api.sessions import ForkSessionRequest


class TestForkSessionRequest:
    def test_turn_index_optional(self):
        # Omitting turn_index forks the entire session (all turns).
        assert ForkSessionRequest().turn_index is None
        assert ForkSessionRequest(turn_index=None).turn_index is None

    def test_explicit_turn_index(self):
        assert ForkSessionRequest(turn_index=0).turn_index == 0
        assert ForkSessionRequest(turn_index=7).turn_index == 7

    def test_negative_turn_index_rejected(self):
        with pytest.raises(ValidationError):
            ForkSessionRequest(turn_index=-1)
