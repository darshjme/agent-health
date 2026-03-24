"""Tests for HealthCheck abstract base."""
import time
import pytest
from agent_health import HealthCheck, HealthResult


class AlwaysHealthy(HealthCheck):
    def check(self) -> HealthResult:
        return HealthResult(name=self.name, status="healthy", message="all good")


class AlwaysUnhealthy(HealthCheck):
    def check(self) -> HealthResult:
        return HealthResult(name=self.name, status="unhealthy", message="broken")


class SlowCheck(HealthCheck):
    def check(self) -> HealthResult:
        time.sleep(10)  # will time out
        return HealthResult(name=self.name, status="healthy")


class ExplodingCheck(HealthCheck):
    def check(self) -> HealthResult:
        raise RuntimeError("boom")


class TestHealthCheck:
    def test_name_property(self):
        c = AlwaysHealthy(name="my-check")
        assert c.name == "my-check"

    def test_critical_default_true(self):
        c = AlwaysHealthy(name="x")
        assert c.critical is True

    def test_critical_false(self):
        c = AlwaysHealthy(name="x", critical=False)
        assert c.critical is False

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            AlwaysHealthy(name="")

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError):
            AlwaysHealthy(name="x", timeout_seconds=-1)

    def test_timeout_enforcement(self):
        c = SlowCheck(name="slow", timeout_seconds=0.1)
        result = c._timed_check()
        assert result.status == "unhealthy"
        assert "timed out" in result.message.lower()

    def test_exception_caught(self):
        c = ExplodingCheck(name="boom")
        result = c._timed_check()
        assert result.status == "unhealthy"
        assert "exception" in result.message.lower()

    def test_duration_recorded(self):
        c = AlwaysHealthy(name="x")
        result = c._timed_check()
        assert result.duration_ms >= 0
