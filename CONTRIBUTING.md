# Contributing to MIF-DAL

Thank you for your interest in contributing to MIF-DAL (Data Abstraction Layer)!

This document provides guidelines and best practices for contributing.

---

## Code of Conduct

### Our Pledge

We pledge to make participation in MIF-DAL a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive Behavior**:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards others

**Unacceptable Behavior**:
- Harassment, trolling, or insulting comments
- Personal or political attacks
- Publishing others' private information
- Other conduct inappropriate in a professional setting

### Enforcement

Instances of abusive behavior may be reported to the project maintainers. All complaints will be reviewed and investigated promptly and fairly.

---

## How Can I Contribute?

### Reporting Bugs

**Before Submitting**:
1. Check existing issues
2. Verify with latest version
3. Gather reproduction steps

**Bug Report Template**:
```markdown
**Environment**:
- MIF-DAL Version: 0.1.0
- Python Version: 3.11
- OS: NixOS 25.11

**Description**:
Clear description of the bug.

**Reproduction Steps**:
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior**:
What should happen.

**Actual Behavior**:
What actually happens.

**Error Output**:
```
[Paste full error traceback]
```
```

---

### Suggesting Features

**Feature Request Template**:
```markdown
**Problem Statement**:
What problem does this feature solve?

**Proposed Solution**:
Describe your proposed feature.

**Alternatives Considered**:
What other solutions did you consider?

**Use Case**:
Real-world scenario where this is useful.
```

---

### Submitting Pull Requests

We welcome code contributions! Follow these steps:

1. **Clone Repository**
   ```bash
   git clone git@github.com:symbioticode/mif-dal.git
   cd mif-dal
   ```

2. **Create Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

3. **Make Changes**
   - Read `halo/project_instructions.md` first
   - Read `halo/anamnese_state.yaml` for current project state
   - Follow specs in `docs/DAL_SPECIFICATION_v1.0.md`
   - Write code
   - Add tests
   - Update documentation

4. **Test Locally**
   ```bash
   ./scripts/dev.sh check
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation only
   - `test:` Adding tests
   - `refactor:` Code refactoring
   - `perf:` Performance improvement
   - `chore:` Maintenance tasks

6. **Push Branch**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Open Pull Request**
   - Go to GitHub repository
   - Click "New Pull Request"
   - Fill out PR template
   - Request review

---

## Development Setup

### Requirements

- Python 3.11+
- NixOS 25.11 (recommended) or Linux with glibc
- git

### Installation

```bash
# Clone repository
git clone git@github.com:symbioticode/mif-dal.git
cd mif-dal

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
./scripts/dev.sh check
```

### Development Tools

**Installed Automatically**:
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `ruff`: Fast linting
- `mypy`: Type checking

**Commands**:
```bash
# Run all gates (ruff + mypy + pytest)
./scripts/dev.sh check

# Run tests only
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=dal --cov-report=html

# Lint code
ruff check dal tests scripts

# Type check
mypy dal
```

---

## Pull Request Process

### Before Submitting

**Checklist**:
- [ ] `./scripts/dev.sh check` passes (ruff + mypy + pytest)
- [ ] `python scripts/adversarial_dal_check_p3.py` — 65/65 PASS
- [ ] New tests added (if applicable)
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow convention
- [ ] PR description is clear

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #123

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
How was this tested?

## Checklist
- [ ] dev.sh check passes
- [ ] adversarial check 65/65
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process

1. **Maintainer Review**: 1-3 days
2. **Feedback**: Address comments
3. **Approval**: At least 1 maintainer approval
4. **Merge**: Squash and merge to main

---

## Coding Standards

### Style Guide

**Python Style**: PEP 8 + Ruff

**Key Rules**:
- Line length: 100 characters
- Indentation: 4 spaces
- Quotes: Double quotes for strings
- Imports: Sorted (ruff)

### Docstrings

**Format**: Google Style

**Required**:
- Module docstring
- Class docstring
- Public method docstring

### Type Hints

**Required** for:
- Function parameters
- Function return types
- Class attributes

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                  # Unit tests (isolate components)
│   ├── test_handoff.py
│   ├── test_pipeline.py
│   └── ...
├── integration/           # Integration tests (end-to-end)
│   ├── test_dal.py
│   └── test_sources.py
└── conftest.py           # Pytest fixtures
```

### Coverage Requirements

- **Minimum**: 80% overall
- **Target**: 93%+ (current baseline)
- **Critical paths**: 100%

**Check Coverage**:
```bash
pytest tests/ --cov=dal --cov-report=html
```

---

## Documentation

### Documentation Types

1. **Code Documentation**: Docstrings (required)
2. **API Reference**: `docs/API.md`
3. **Architecture**: `docs/ARCHITECTURE.md`
4. **Specification**: `docs/DAL_SPECIFICATION_v1.0.md`

### Updating Documentation

**When to Update**:
- New feature → Add example + API docs
- Bug fix → Update existing docs if wrong
- Breaking change → Update all affected docs

---

## Project Architecture

MIF-DAL follows the Metric Integrity Framework pipeline:

```
Source Adapters → Resolver → Pipeline → DALHandoff → Caller
     (fetch)    (fallback)  (DQF gate)   (frozen)
```

Key architectural decisions are documented in `halo/anamnese_state.yaml` (section `decisions_immuables`). Do not modify them without escalation.

---

## Questions?

- **GitHub Issues**: Report bugs, request features
- **Email**: corail.synergia@proton.me

---

**Thank you for contributing to MIF-DAL!**
