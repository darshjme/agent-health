"""Built-in health check implementations.

All checks use only the Python standard library (no psutil, no third-party deps).
"""

from __future__ import annotations

import shutil
import time
import urllib.error
import urllib.request
from typing import Callable

from .core import HealthCheck, HealthResult


# ---------------------------------------------------------------------------
# HttpCheck
# ---------------------------------------------------------------------------

class HttpCheck(HealthCheck):
    """Check that an HTTP endpoint returns the expected status code."""

    def __init__(
        self,
        name: str,
        url: str,
        expected_status: int = 200,
        timeout: float = 5.0,
        critical: bool = True,
    ) -> None:
        super().__init__(name=name, timeout_seconds=timeout, critical=critical)
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://. Got: {url!r}")
        self._url = url
        self._expected_status = expected_status

    @property
    def url(self) -> str:
        return self._url

    def check(self) -> HealthResult:
        start = time.perf_counter()
        try:
            req = urllib.request.Request(self._url, method="GET")
            with urllib.request.urlopen(req, timeout=self._timeout_seconds) as resp:
                status = resp.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        except Exception as exc:  # noqa: BLE001
            return HealthResult(
                name=self.name,
                status="unhealthy",
                message=f"HTTP request failed: {exc}",
                metadata={"url": self._url},
            )

        duration_ms = (time.perf_counter() - start) * 1000

        if status == self._expected_status:
            return HealthResult(
                name=self.name,
                status="healthy",
                message=f"HTTP {status} from {self._url}",
                duration_ms=duration_ms,
                metadata={"url": self._url, "status_code": status},
            )
        return HealthResult(
            name=self.name,
            status="unhealthy",
            message=(
                f"Expected HTTP {self._expected_status}, "
                f"got {status} from {self._url}"
            ),
            duration_ms=duration_ms,
            metadata={"url": self._url, "status_code": status, "expected": self._expected_status},
        )


# ---------------------------------------------------------------------------
# DiskSpaceCheck
# ---------------------------------------------------------------------------

class DiskSpaceCheck(HealthCheck):
    """Check that a filesystem path has at least `min_free_gb` free space."""

    def __init__(
        self,
        name: str,
        path: str = "/",
        min_free_gb: float = 1.0,
        critical: bool = True,
        timeout: float = 5.0,
    ) -> None:
        super().__init__(name=name, timeout_seconds=timeout, critical=critical)
        self._path = path
        self._min_free_gb = min_free_gb

    def check(self) -> HealthResult:
        try:
            usage = shutil.disk_usage(self._path)
        except Exception as exc:  # noqa: BLE001
            return HealthResult(
                name=self.name,
                status="unhealthy",
                message=f"Could not read disk usage for '{self._path}': {exc}",
                metadata={"path": self._path},
            )

        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        used_pct = (usage.used / usage.total) * 100 if usage.total > 0 else 0.0

        meta = {
            "path": self._path,
            "free_gb": round(free_gb, 3),
            "total_gb": round(total_gb, 3),
            "used_percent": round(used_pct, 2),
            "min_free_gb": self._min_free_gb,
        }

        if free_gb >= self._min_free_gb:
            return HealthResult(
                name=self.name,
                status="healthy",
                message=f"{free_gb:.2f} GB free on '{self._path}'",
                metadata=meta,
            )
        return HealthResult(
            name=self.name,
            status="unhealthy",
            message=(
                f"Only {free_gb:.2f} GB free on '{self._path}' "
                f"(minimum required: {self._min_free_gb} GB)"
            ),
            metadata=meta,
        )


# ---------------------------------------------------------------------------
# MemoryCheck
# ---------------------------------------------------------------------------

class MemoryCheck(HealthCheck):
    """Check that system memory usage is below `max_percent`."""

    def __init__(
        self,
        name: str,
        max_percent: float = 90.0,
        critical: bool = True,
        timeout: float = 5.0,
    ) -> None:
        super().__init__(name=name, timeout_seconds=timeout, critical=critical)
        if not (0 < max_percent <= 100):
            raise ValueError("max_percent must be between 0 (exclusive) and 100 (inclusive).")
        self._max_percent = max_percent

    def _read_meminfo(self) -> dict[str, int]:
        """Parse /proc/meminfo on Linux; fallback to ResourceWarning on other OSes."""
        import platform
        if platform.system() != "Linux":
            # Fallback: use resource module (not always accurate, but zero-dep)
            raise OSError("MemoryCheck via /proc/meminfo is Linux-only.")

        meminfo: dict[str, int] = {}
        with open("/proc/meminfo", "r") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    try:
                        meminfo[key] = int(parts[1])
                    except ValueError:
                        pass
        return meminfo

    def check(self) -> HealthResult:
        try:
            meminfo = self._read_meminfo()
            total_kb = meminfo.get("MemTotal", 0)
            available_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))

            if total_kb == 0:
                return HealthResult(
                    name=self.name,
                    status="degraded",
                    message="Could not determine total memory from /proc/meminfo.",
                )

            used_kb = total_kb - available_kb
            used_pct = (used_kb / total_kb) * 100
        except OSError:
            # Non-Linux: try mmap / ctypes approach — graceful degradation
            return HealthResult(
                name=self.name,
                status="degraded",
                message="MemoryCheck is only fully supported on Linux (/proc/meminfo). Skipping.",
                metadata={"platform": __import__("platform").system()},
            )
        except Exception as exc:  # noqa: BLE001
            return HealthResult(
                name=self.name,
                status="unhealthy",
                message=f"Failed to read memory info: {exc}",
            )

        meta = {
            "total_mb": round(total_kb / 1024, 1),
            "used_mb": round(used_kb / 1024, 1),
            "available_mb": round(available_kb / 1024, 1),
            "used_percent": round(used_pct, 2),
            "max_percent": self._max_percent,
        }

        if used_pct <= self._max_percent:
            return HealthResult(
                name=self.name,
                status="healthy",
                message=f"Memory usage {used_pct:.1f}% (limit: {self._max_percent}%)",
                metadata=meta,
            )
        return HealthResult(
            name=self.name,
            status="unhealthy",
            message=(
                f"Memory usage {used_pct:.1f}% exceeds limit {self._max_percent}%"
            ),
            metadata=meta,
        )


# ---------------------------------------------------------------------------
# LatencyCheck
# ---------------------------------------------------------------------------

class LatencyCheck(HealthCheck):
    """Measure the latency of a callable and fail if it exceeds `max_ms`."""

    def __init__(
        self,
        name: str,
        func: Callable[[], object],
        max_ms: float = 1000.0,
        critical: bool = True,
        timeout: float = 5.0,
    ) -> None:
        super().__init__(name=name, timeout_seconds=timeout, critical=critical)
        if not callable(func):
            raise TypeError("func must be callable.")
        if max_ms <= 0:
            raise ValueError("max_ms must be positive.")
        self._func = func
        self._max_ms = max_ms

    def check(self) -> HealthResult:
        start = time.perf_counter()
        try:
            self._func()
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - start) * 1000
            return HealthResult(
                name=self.name,
                status="unhealthy",
                message=f"Callable raised an exception: {exc}",
                duration_ms=elapsed_ms,
                metadata={"max_ms": self._max_ms},
            )
        elapsed_ms = (time.perf_counter() - start) * 1000

        meta = {
            "latency_ms": round(elapsed_ms, 3),
            "max_ms": self._max_ms,
        }

        if elapsed_ms <= self._max_ms:
            return HealthResult(
                name=self.name,
                status="healthy",
                message=f"Latency {elapsed_ms:.1f}ms (limit: {self._max_ms}ms)",
                duration_ms=elapsed_ms,
                metadata=meta,
            )
        return HealthResult(
            name=self.name,
            status="unhealthy",
            message=(
                f"Latency {elapsed_ms:.1f}ms exceeds limit {self._max_ms}ms"
            ),
            duration_ms=elapsed_ms,
            metadata=meta,
        )
