"""Tests for built-in health checks."""
import time
import pytest
from unittest.mock import patch, MagicMock
from agent_health import HttpCheck, DiskSpaceCheck, MemoryCheck, LatencyCheck
from agent_health.core import HealthResult


# ---------------------------------------------------------------------------
# HttpCheck
# ---------------------------------------------------------------------------

class TestHttpCheck:
    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            HttpCheck(name="x", url="ftp://example.com")

    def test_healthy_on_expected_status(self):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200

        with patch("urllib.request.urlopen", return_value=mock_resp):
            c = HttpCheck(name="api", url="http://example.com")
            result = c.check()

        assert result.status == "healthy"
        assert result.metadata["status_code"] == 200

    def test_unhealthy_on_wrong_status(self):
        import urllib.error
        err = urllib.error.HTTPError(
            url="http://example.com", code=500, msg="Error", hdrs=None, fp=None
        )
        with patch("urllib.request.urlopen", side_effect=err):
            c = HttpCheck(name="api", url="http://example.com", expected_status=200)
            result = c.check()

        assert result.status == "unhealthy"
        assert result.metadata["status_code"] == 500

    def test_connection_error_is_unhealthy(self):
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            c = HttpCheck(name="api", url="http://example.com")
            result = c.check()

        assert result.status == "unhealthy"
        assert "connection refused" in result.message

    def test_non_200_expected_status_passes(self):
        import urllib.error
        err = urllib.error.HTTPError(
            url="http://example.com", code=404, msg="Not Found", hdrs=None, fp=None
        )
        with patch("urllib.request.urlopen", side_effect=err):
            c = HttpCheck(name="api", url="http://example.com", expected_status=404)
            result = c.check()

        assert result.status == "healthy"


# ---------------------------------------------------------------------------
# DiskSpaceCheck
# ---------------------------------------------------------------------------

class TestDiskSpaceCheck:
    def _usage(self, total_gb, free_gb):
        """Return a fake shutil.disk_usage namedtuple."""
        total = int(total_gb * 1024 ** 3)
        free = int(free_gb * 1024 ** 3)
        used = total - free
        DU = type("DU", (), {"total": total, "used": used, "free": free})
        return DU()

    def test_enough_disk_is_healthy(self):
        with patch("shutil.disk_usage", return_value=self._usage(100, 50)):
            c = DiskSpaceCheck(name="disk", path="/", min_free_gb=1.0)
            result = c.check()
        assert result.status == "healthy"

    def test_insufficient_disk_is_unhealthy(self):
        with patch("shutil.disk_usage", return_value=self._usage(100, 0.5)):
            c = DiskSpaceCheck(name="disk", path="/", min_free_gb=1.0)
            result = c.check()
        assert result.status == "unhealthy"

    def test_exact_minimum_passes(self):
        with patch("shutil.disk_usage", return_value=self._usage(100, 1.0)):
            c = DiskSpaceCheck(name="disk", path="/", min_free_gb=1.0)
            result = c.check()
        assert result.status == "healthy"

    def test_os_error_is_unhealthy(self):
        with patch("shutil.disk_usage", side_effect=FileNotFoundError("no such path")):
            c = DiskSpaceCheck(name="disk", path="/nonexistent")
            result = c.check()
        assert result.status == "unhealthy"

    def test_metadata_present(self):
        with patch("shutil.disk_usage", return_value=self._usage(100, 50)):
            c = DiskSpaceCheck(name="disk")
            result = c.check()
        assert "free_gb" in result.metadata
        assert "total_gb" in result.metadata


# ---------------------------------------------------------------------------
# MemoryCheck
# ---------------------------------------------------------------------------

class TestMemoryCheck:
    MEMINFO_NORMAL = (
        "MemTotal:       16000000 kB\n"
        "MemFree:         2000000 kB\n"
        "MemAvailable:    8000000 kB\n"
    )
    MEMINFO_HIGH = (
        "MemTotal:       16000000 kB\n"
        "MemFree:          100000 kB\n"
        "MemAvailable:     100000 kB\n"
    )

    def _patch_meminfo(self, content):
        from unittest.mock import mock_open
        return patch("builtins.open", mock_open(read_data=content))

    def test_invalid_max_percent_raises(self):
        with pytest.raises(ValueError):
            MemoryCheck(name="mem", max_percent=0)

    def test_healthy_when_usage_low(self):
        with self._patch_meminfo(self.MEMINFO_NORMAL):
            with patch("platform.system", return_value="Linux"):
                c = MemoryCheck(name="mem", max_percent=90.0)
                result = c.check()
        assert result.status == "healthy"

    def test_unhealthy_when_usage_high(self):
        with self._patch_meminfo(self.MEMINFO_HIGH):
            with patch("platform.system", return_value="Linux"):
                c = MemoryCheck(name="mem", max_percent=90.0)
                result = c.check()
        assert result.status == "unhealthy"

    def test_non_linux_degrades_gracefully(self):
        with patch("platform.system", return_value="Darwin"):
            c = MemoryCheck(name="mem")
            result = c.check()
        assert result.status == "degraded"


# ---------------------------------------------------------------------------
# LatencyCheck
# ---------------------------------------------------------------------------

class TestLatencyCheck:
    def test_fast_callable_is_healthy(self):
        c = LatencyCheck(name="fast", func=lambda: None, max_ms=1000.0)
        result = c.check()
        assert result.status == "healthy"

    def test_slow_callable_is_unhealthy(self):
        def slow():
            time.sleep(0.2)

        c = LatencyCheck(name="slow", func=slow, max_ms=10.0)
        result = c.check()
        assert result.status == "unhealthy"
        assert "exceeds" in result.message.lower()

    def test_raising_callable_is_unhealthy(self):
        def boom():
            raise ValueError("error")

        c = LatencyCheck(name="boom", func=boom, max_ms=1000.0)
        result = c.check()
        assert result.status == "unhealthy"

    def test_non_callable_raises(self):
        with pytest.raises(TypeError):
            LatencyCheck(name="x", func="not-callable", max_ms=100.0)

    def test_negative_max_ms_raises(self):
        with pytest.raises(ValueError):
            LatencyCheck(name="x", func=lambda: None, max_ms=-1)

    def test_metadata_contains_latency(self):
        c = LatencyCheck(name="lat", func=lambda: None, max_ms=1000.0)
        result = c.check()
        assert "latency_ms" in result.metadata
        assert "max_ms" in result.metadata
