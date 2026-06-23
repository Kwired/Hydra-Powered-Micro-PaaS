# Contributing to HydraLite

We welcome community contributions to the HydraLite ecosystem! Whether you are fixing a typo in our GitBook documentation or submitting a brand new use-case template for the community, this guide will help you navigate the process.

## Pull Request Process

1. **Fork the Repository:** Create a fork of the `Kwired/Hydra-Powered-Micro-PaaS` repository on GitHub.
2. **Branch Naming:** Create a feature branch named `feature/your-feature-name` or `fix/your-bug-fix`.
3. **Commit Messages:** Use clear, descriptive commit messages.
4. **Submit the PR:** Open a Pull Request against the `main` branch. A maintainer will review your code within 48 hours.

## Code Standards

To maintain a secure and performant L2 architecture, all Python code must adhere to the following standards:
- **Type Hinting:** All functions must include Python type hints.
- **AsyncIO:** Because we rely on high-frequency WebSockets, all I/O bound functions must be asynchronous. Do not introduce blocking code.
- **Documentation:** All new modules must include clear docstrings explaining the UTXO flow.

## Testing Requirements

Security is our top priority. **Your Pull Request will be automatically rejected if it breaks the test suite.**

Before submitting your PR, you must run the local test suite:

```bash
source .venv/bin/activate
pytest tests/ -v
```

If you are submitting a new feature, you must include a new unit test in the `tests/` directory that covers your logic.

## Submitting Custom Templates

If you are contributing a new use-case template (e.g., a specific DEX plugin or NFT auction mechanic), please place your logic inside the `templates/` directory. Do not clutter the core `api/` engine with project-specific logic.
