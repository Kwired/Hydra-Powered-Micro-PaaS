# Contributor Guidelines: Template Development

This guide describes how to author, test, and contribute custom application templates to the HydraLite ecosystem.

---

## What is a HydraLite Template?

A template is a self-contained domain module that executes on top of the HydraLite Micro-PaaS engine. Rather than altering core infrastructure code (`api/` or `autoscaler/`), use-case-specific business logic is packaged into modular templates inside the `templates/` directory.

Common use cases include:
- High-throughput parallel NFT minting engines
- Micro-payment paywall gateways for digital content
- Rapid auction and bid matching channels
- Game turn validation channels
- Oracle data publishing pipelines

---

## Template Directory Structure

All new templates must reside in a dedicated folder under `templates/`:

```
templates/
└── <template_name>/
    ├── README.md           # Architecture overview and usage instructions
    ├── config.yaml         # Action definitions, pricing, and parameters
    ├── engine.py           # Core business logic (asynchronous)
    ├── routes.py           # Optional FastAPI APIRouter endpoints
    └── tests/
        ├── __init__.py
        └── test_engine.py  # Unit and integration test suite
```

---

## Engineering Standards

To ensure reliability in production environments, code submitted via Pull Requests must meet the following criteria:

### 1. Asynchronous I/O Only
HydraLite operates over non-blocking WebSocket and HTTP connections. Never use blocking calls like `time.sleep()`, synchronous `requests.get()`, or blocking file system I/O inside request handlers. Use `asyncio.sleep()`, `httpx.AsyncClient`, or `aiofiles`.

```python
# Correct
import asyncio
import httpx

async def submit_batch(payload: dict) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post("http://hydralite-api:8000/api/v1/pay", json=payload)
        return response.json()["tx_id"]
```

### 2. Strict Type Annotations
All functions, parameters, and return types must include standard Python type annotations. Run `mypy` locally to ensure zero typing errors.

### 3. Clear Exception Handling
Catch domain-specific exceptions and map them to explicit HTTP status codes or logged error states. Never write bare `except:` clauses.

### 4. Test Coverage
Every template must include automated unit tests under `tests/`. We enforce a minimum **80% branch coverage** threshold for all newly submitted template directories.

Run tests locally:
```bash
pytest templates/<template_name>/tests/ -v --cov=templates/<template_name>
```

---

## Submitting a Pull Request

1. **Fork the Repository**: Create a fork of `https://github.com/Kwired/Hydra-Powered-Micro-PaaS`.
2. **Create a Feature Branch**:
   ```bash
   git checkout -b template/your-template-name
   ```
3. **Write Conventional Commits**:
   - `feat(template): add high-speed auction settlement engine`
   - `test(template): add unit tests for bid state channel`
   - `docs(template): update installation instructions`
4. **Run Pre-Commit Checks**:
   Ensure linting and tests pass cleanly:
   ```bash
   flake8 templates/<template_name>
   pytest templates/<template_name>/tests/
   ```
5. **Open a PR**: Submit your Pull Request against the `main` branch. Maintainers review community submissions on a weekly cadence.
