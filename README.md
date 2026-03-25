<div align="center">

<img src="assets/agent-health-hero.png" alt="agent-health — Vedic Arsenal by Darshankumar Joshi" width="100%" />

# 🔮 agent-health

<h3><em>आरोग्य</em></h3>

> *Arogya — the Vedic science of system wellness*

**Health checks and liveness monitoring for LLM agent systems — HTTP, disk, memory, latency checks with parallel execution. Zero dependencies.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen?style=flat-square)](https://github.com/darshjme/agent-health)
[![Tests](https://img.shields.io/badge/Tests-Passing-success?style=flat-square)](https://github.com/darshjme/agent-health/actions)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)](LICENSE)
[![Vedic Arsenal](https://img.shields.io/badge/Vedic%20Arsenal-100%20libs-purple?style=flat-square)](https://github.com/darshjme/arsenal)

*Part of the [**Vedic Arsenal**](https://github.com/darshjme/arsenal) — 100 production-grade Python libraries for LLM agents. Zero dependencies. Battle-tested.*

</div>

---

## Overview

`agent-health` implements **health checks and liveness monitoring for llm agent systems — http, disk, memory, latency checks with parallel execution. zero dependencies.**

Inspired by the Vedic principle of *आरोग्य* (Arogya), this library brings the ancient wisdom of structured discipline to modern LLM agent engineering.

No external dependencies. Pure Python 3.8+. Drop it in anywhere.

## Installation

```bash
pip install agent-health
```

Or clone directly:
```bash
git clone https://github.com/darshjme/agent-health.git
cd agent-health
pip install -e .
```

## How It Works

```mermaid
flowchart TD
    A[agent-health] --> B[HTTP Check]
    A --> C[Disk Check]
    A --> D[Memory Check]
    A --> E[Latency Check]
    B & C & D & E --> F{All Healthy?}
    F -- Yes --> G[HEALTHY]
    F -- No --> H[DEGRADED / DOWN]
    style A fill:#6b21a8,color:#fff
```

## Quick Start

```python
from health import *

# Initialize
# See examples/ for full usage patterns
```

## Why `agent-health`?

Production LLM systems fail in predictable ways. `agent-health` solves the **health** failure mode with:

- **Zero dependencies** — no version conflicts, no bloat
- **Battle-tested patterns** — extracted from real production systems
- **Type-safe** — full type hints, mypy-compatible
- **Minimal surface area** — one job, done well
- **Composable** — works with any LLM framework (LangChain, LlamaIndex, raw OpenAI, etc.)

## The Vedic Arsenal

`agent-health` is part of **[darshjme/arsenal](https://github.com/darshjme/arsenal)** — a collection of 100 focused Python libraries for LLM agent infrastructure.

Each library solves exactly one problem. Together they form a complete stack.

```
pip install agent-health  # this library
# Browse all 100: https://github.com/darshjme/arsenal
```

## Contributing

Found a bug? Have an improvement?

1. Fork the repo
2. Create a feature branch (`git checkout -b fix/your-fix`)
3. Add tests
4. Open a PR

All contributions welcome. Keep it zero-dependency.

## License

MIT — use freely, build freely.

---

<div align="center">

**Built with 🔮 by [Darshankumar Joshi](https://github.com/darshjme)** · [@thedarshanjoshi](https://twitter.com/thedarshanjoshi)

*"कर्मण्येवाधिकारस्ते मा फलेषु कदाचन"*
*Your right is to action alone, never to the fruits thereof.*

[Arsenal](https://github.com/darshjme/arsenal) · [GitHub](https://github.com/darshjme) · [Twitter](https://twitter.com/thedarshanjoshi)

</div>
