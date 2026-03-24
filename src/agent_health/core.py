"""Core abstractions for agent-health: HealthCheck, HealthResult, HealthRegistry, SystemHealth."""

from __future__ import annotations

import time
import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# HealthResult
# ---------------------------------------------------------------------------

@dataclass
class HealthResult:
    """Result of a single health check."""

    name: str
    status: str  # "healthy" | "degraded" | "unhealthy"
    message: str = ""
    duration_ms: float = 0.0
    metadata: Optional[dict] = field(default=None)

    VALID_STATUSES = frozenset({"healthy", "degraded", "unhealthy"})

    def __post_init__(self) -> None:
        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of {sorted(self.VALID_STATUSES)}."
            )
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_healthy(self) -> bool:
        """True only when status is 'healthy'."""
        return self.status == "healthy"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 3),
            "metadata": self.metadata or {},
        }


# ---------------------------------------------------------------------------
# HealthCheck (abstract base)
# ---------------------------------------------------------------------------

class HealthCheck(ABC):
    """Abstract base class for individual health checks."""

    def __init__(
        self,
        name: str,
        timeout_seconds: float = 5.0,
        critical: bool = True,
    ) -> None:
        if not name or not name.strip():
            raise ValueError("HealthCheck name must be a non-empty string.")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        self._name = name
        self._timeout_seconds = timeout_seconds
        self._critical = critical

    @property
    def name(self) -> str:
        return self._name

    @property
    def critical(self) -> bool:
        return self._critical

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    @abstractmethod
    def check(self) -> HealthResult:
        """Execute the health check and return a HealthResult."""

    def _timed_check(self) -> HealthResult:
        """Run check(), enforce timeout, and record duration_ms."""
        result_holder: list[HealthResult] = []
        exc_holder: list[BaseException] = []

        def _target() -> None:
            try:
                result_holder.append(self.check())
            except Exception as exc:  # noqa: BLE001
                exc_holder.append(exc)

        t = threading.Thread(target=_target, daemon=True)
        start = time.perf_counter()
        t.start()
        t.join(timeout=self._timeout_seconds)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if t.is_alive():
            return HealthResult(
                name=self._name,
                status="unhealthy",
                message=f"Check timed out after {self._timeout_seconds}s",
                duration_ms=elapsed_ms,
            )
        if exc_holder:
            return HealthResult(
                name=self._name,
                status="unhealthy",
                message=f"Check raised an exception: {exc_holder[0]}",
                duration_ms=elapsed_ms,
            )
        result = result_holder[0]
        result.duration_ms = elapsed_ms
        return result


# ---------------------------------------------------------------------------
# SystemHealth
# ---------------------------------------------------------------------------

@dataclass
class SystemHealth:
    """Aggregated result of all health checks."""

    status: str  # "healthy" | "degraded" | "unhealthy"
    checks: list[HealthResult]
    timestamp: float
    duration_ms: float

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "healthy")

    @property
    def degraded_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "degraded")

    @property
    def unhealthy_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "unhealthy")

    @property
    def critical_failures(self) -> list[HealthResult]:
        """Only checks that are critical AND unhealthy/degraded."""
        return [c for c in self.checks if c.status != "healthy"]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "timestamp": self.timestamp,
            "duration_ms": round(self.duration_ms, 3),
            "summary": {
                "healthy": self.healthy_count,
                "degraded": self.degraded_count,
                "unhealthy": self.unhealthy_count,
                "total": len(self.checks),
            },
            "checks": [c.to_dict() for c in self.checks],
        }


# ---------------------------------------------------------------------------
# HealthRegistry
# ---------------------------------------------------------------------------

class HealthRegistry:
    """Runs and aggregates all registered health checks."""

    def __init__(self) -> None:
        self._checks: dict[str, HealthCheck] = {}
        self._lock = threading.Lock()

    def register(self, check: HealthCheck) -> None:
        """Register a health check. Raises if name already registered."""
        if not isinstance(check, HealthCheck):
            raise TypeError(f"Expected a HealthCheck instance, got {type(check).__name__}.")
        with self._lock:
            if check.name in self._checks:
                raise ValueError(f"A check named '{check.name}' is already registered.")
            self._checks[check.name] = check

    def unregister(self, name: str) -> None:
        """Remove a check by name. Raises if not found."""
        with self._lock:
            if name not in self._checks:
                raise KeyError(f"No check named '{name}' is registered.")
            del self._checks[name]

    def list_checks(self) -> list[str]:
        """Return sorted list of registered check names."""
        with self._lock:
            return sorted(self._checks.keys())

    def run_check(self, name: str) -> HealthResult:
        """Run a single named check. Raises KeyError if not found."""
        with self._lock:
            check = self._checks.get(name)
        if check is None:
            raise KeyError(f"No check named '{name}' is registered.")
        return check._timed_check()

    def run_all(self, parallel: bool = False) -> SystemHealth:
        """
        Run all registered checks and return an aggregated SystemHealth.

        Parameters
        ----------
        parallel : bool
            If True, checks run concurrently via a ThreadPoolExecutor.
        """
        with self._lock:
            checks_snapshot = list(self._checks.values())

        start = time.perf_counter()
        timestamp = time.time()

        if parallel and len(checks_snapshot) > 1:
            results = self._run_parallel(checks_snapshot)
        else:
            results = [c._timed_check() for c in checks_snapshot]

        elapsed_ms = (time.perf_counter() - start) * 1000
        status = self._aggregate_status(results, checks_snapshot)

        return SystemHealth(
            status=status,
            checks=results,
            timestamp=timestamp,
            duration_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run_parallel(checks: list[HealthCheck]) -> list[HealthResult]:
        results: dict[str, HealthResult] = {}
        with ThreadPoolExecutor(max_workers=min(len(checks), 32)) as executor:
            future_to_check = {executor.submit(c._timed_check): c for c in checks}
            for future in as_completed(future_to_check):
                check = future_to_check[future]
                try:
                    results[check.name] = future.result()
                except Exception as exc:  # noqa: BLE001
                    results[check.name] = HealthResult(
                        name=check.name,
                        status="unhealthy",
                        message=f"Unexpected executor error: {exc}",
                    )
        # Preserve registration order
        return [results[c.name] for c in checks if c.name in results]

    @staticmethod
    def _aggregate_status(
        results: list[HealthResult], checks: list[HealthCheck]
    ) -> str:
        critical_names = {c.name for c in checks if c.critical}
        for result in results:
            if result.status != "healthy" and result.name in critical_names:
                return "unhealthy"
        for result in results:
            if result.status != "healthy":
                return "degraded"
        return "healthy"
