# Changelog

All notable changes to `agent-health` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2024-03-24

### Added
- `HealthResult` dataclass with `is_healthy` property and `to_dict()`.
- `HealthCheck` abstract base class with timeout enforcement via thread.
- `HealthRegistry` with sequential and parallel (`ThreadPoolExecutor`) execution.
- `SystemHealth` aggregated result with `healthy_count`, `degraded_count`, `unhealthy_count`, `critical_failures`, and `to_dict()`.
- Status aggregation logic: critical failures → "unhealthy"; non-critical failures → "degraded"; all pass → "healthy".
- Built-in checks: `HttpCheck`, `DiskSpaceCheck`, `MemoryCheck`, `LatencyCheck`.
- Zero runtime dependencies (uses only Python standard library).
- Full pytest test suite (22+ tests).
