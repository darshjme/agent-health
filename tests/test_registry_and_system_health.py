"""Tests for HealthRegistry and SystemHealth."""
import pytest
from agent_health import HealthCheck, HealthResult, HealthRegistry, SystemHealth


# ---- Helpers ----

class FixedCheck(HealthCheck):
    def __init__(self, name, status, critical=True):
        super().__init__(name=name, critical=critical)
        self._status = status

    def check(self) -> HealthResult:
        return HealthResult(name=self.name, status=self._status)


class TestHealthRegistry:
    def _registry(self):
        return HealthRegistry()

    def test_register_and_list(self):
        r = self._registry()
        r.register(FixedCheck("a", "healthy"))
        r.register(FixedCheck("b", "healthy"))
        assert r.list_checks() == ["a", "b"]

    def test_register_duplicate_raises(self):
        r = self._registry()
        r.register(FixedCheck("x", "healthy"))
        with pytest.raises(ValueError, match="already registered"):
            r.register(FixedCheck("x", "healthy"))

    def test_unregister(self):
        r = self._registry()
        r.register(FixedCheck("a", "healthy"))
        r.unregister("a")
        assert "a" not in r.list_checks()

    def test_unregister_missing_raises(self):
        r = self._registry()
        with pytest.raises(KeyError):
            r.unregister("nonexistent")

    def test_run_check_single(self):
        r = self._registry()
        r.register(FixedCheck("ping", "healthy"))
        result = r.run_check("ping")
        assert result.name == "ping"
        assert result.status == "healthy"

    def test_run_check_missing_raises(self):
        r = self._registry()
        with pytest.raises(KeyError):
            r.run_check("ghost")

    def test_run_all_returns_system_health(self):
        r = self._registry()
        r.register(FixedCheck("a", "healthy"))
        sh = r.run_all()
        assert isinstance(sh, SystemHealth)

    def test_run_all_parallel(self):
        r = self._registry()
        for i in range(5):
            r.register(FixedCheck(f"c{i}", "healthy"))
        sh = r.run_all(parallel=True)
        assert sh.healthy_count == 5

    def test_register_non_check_raises(self):
        r = self._registry()
        with pytest.raises(TypeError):
            r.register("not-a-check")  # type: ignore


class TestSystemHealthAggregation:
    def _run(self, checks):
        r = HealthRegistry()
        for c in checks:
            r.register(c)
        return r.run_all()

    def test_all_healthy(self):
        sh = self._run([FixedCheck("a", "healthy"), FixedCheck("b", "healthy")])
        assert sh.status == "healthy"
        assert sh.healthy_count == 2

    def test_critical_failure_makes_unhealthy(self):
        sh = self._run([
            FixedCheck("a", "healthy"),
            FixedCheck("b", "unhealthy", critical=True),
        ])
        assert sh.status == "unhealthy"

    def test_non_critical_failure_makes_degraded(self):
        sh = self._run([
            FixedCheck("a", "healthy"),
            FixedCheck("b", "unhealthy", critical=False),
        ])
        assert sh.status == "degraded"

    def test_counts(self):
        sh = self._run([
            FixedCheck("h", "healthy"),
            FixedCheck("d", "degraded", critical=False),
            FixedCheck("u", "unhealthy", critical=False),
        ])
        assert sh.healthy_count == 1
        assert sh.degraded_count == 1
        assert sh.unhealthy_count == 1

    def test_critical_failures_property(self):
        sh = self._run([
            FixedCheck("ok", "healthy"),
            FixedCheck("fail", "unhealthy", critical=True),
        ])
        failures = sh.critical_failures
        assert any(f.name == "fail" for f in failures)

    def test_to_dict_structure(self):
        sh = self._run([FixedCheck("a", "healthy")])
        d = sh.to_dict()
        assert "status" in d
        assert "checks" in d
        assert "timestamp" in d
        assert "duration_ms" in d
        assert "summary" in d

    def test_empty_registry_is_healthy(self):
        r = HealthRegistry()
        sh = r.run_all()
        assert sh.status == "healthy"
        assert sh.healthy_count == 0
