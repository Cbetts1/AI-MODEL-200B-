# Contributing to AURA

Thank you for your interest in making AURA better!  AURA was founded by
**Christopher Betts** with one goal: **make AI and its services free to the
public**.  Every contribution — no matter how small — moves us closer to
that goal.

---

## How to Contribute

### 1. Report Bugs

Open an [issue](https://github.com/Cbetts1/AI-MODEL-200B-/issues) with:

- A clear title and description.
- Steps to reproduce the problem.
- Expected vs. actual behaviour.
- Your OS and Python version.

### 2. Suggest Features

Open an issue tagged **enhancement** and describe:

- What you'd like AURA to do.
- Why it would help the community.
- Any ideas on implementation (optional).

### 3. Submit Code

1. **Fork** the repository and create a branch from `main`.
2. **Install** the dev environment:
   ```bash
   pip install -e .
   pip install pytest
   ```
3. **Make your changes** — keep them focused and small.
4. **Add or update tests** in `tests/` for any new behaviour.
5. **Run the test suite**:
   ```bash
   pytest tests/ -v
   ```
6. **Open a Pull Request** against `main` with a clear description.

### 4. Improve Documentation

Docs live in `docs/` and `README.md`.  Typo fixes, better examples, and
translations are always welcome.

---

## Code Style

- Python 3.9+ compatible.
- Follow PEP 8 naming conventions.
- Keep imports grouped: stdlib → third-party → local.
- Match the style of surrounding code.

---

## Code of Conduct

All contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
Be kind, be respectful, and remember that AURA is here to help everyone.

---

## License

By contributing you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE), the same licence as the rest of AURA.
