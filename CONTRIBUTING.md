# Contributing to agent-health

Thank you for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/your-org/agent-health
cd agent-health
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
python -m pytest tests/ -v
```

All tests must pass before submitting a pull request.

## Code Style

- Follow PEP 8.
- Use type annotations everywhere.
- Keep zero runtime dependencies — use only the Python standard library.

## Submitting Changes

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/my-feature`.
3. Write tests for all new functionality.
4. Ensure all tests pass.
5. Open a pull request against `main` with a clear description.

## Adding a New Built-in Check

1. Create your subclass in `src/agent_health/checks.py`.
2. Import and re-export it in `src/agent_health/__init__.py`.
3. Write at least 3 pytest tests (healthy path, unhealthy path, edge cases).

## Reporting Issues

Open an issue on GitHub with:
- Python version
- OS
- Minimal reproducible example
- Expected vs. actual behaviour
