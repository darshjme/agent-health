"""Tests for HealthResult."""
import pytest
from agent_health import HealthResult


class TestHealthResult:
    def test_healthy_status(self):
        r = HealthResult(name="db", status="healthy")
        assert r.status == "healthy"
        assert r.is_healthy is True

    def test_degraded_status(self):
        r = HealthResult(name="db", status="degraded")
        assert r.is_healthy is False

    def test_unhealthy_status(self):
        r = HealthResult(name="db", status="unhealthy")
        assert r.is_healthy is False

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="Invalid status"):
            HealthResult(name="db", status="broken")

    def test_metadata_defaults_to_empty_dict(self):
        r = HealthResult(name="db", status="healthy")
        assert r.metadata == {}

    def test_to_dict_structure(self):
        r = HealthResult(
            name="api",
            status="healthy",
            message="OK",
            duration_ms=12.345,
            metadata={"key": "value"},
        )
        d = r.to_dict()
        assert d["name"] == "api"
        assert d["status"] == "healthy"
        assert d["message"] == "OK"
        assert d["duration_ms"] == 12.345
        assert d["metadata"] == {"key": "value"}

    def test_to_dict_rounds_duration(self):
        r = HealthResult(name="x", status="healthy", duration_ms=1.23456789)
        assert r.to_dict()["duration_ms"] == 1.235
