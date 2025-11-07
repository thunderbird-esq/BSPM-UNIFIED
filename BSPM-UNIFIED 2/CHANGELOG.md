# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.4.0] - 2025-11-07

### Added - Critical Fixes
- `.gitignore` file with comprehensive patterns for Python, Docker, and project-specific files
- CI/CD pipeline with GitHub Actions (lint, test, security, docker-build jobs)
- Dependabot configuration for automated dependency updates
- Modular router architecture replacing monolithic main.py (1,163 → 154 lines)
- `backend/routers/` package with feature-based routers (health, chat, generation, sprites, batch, admin)
- `backend/models.py` for centralized Pydantic schemas
- `backend/dependencies.py` for shared configuration and utilities

### Added - High Priority Security
- Bcrypt hashing for API keys (replacing plaintext storage)
- `APIKeyManager` with `hash_key()` and `validate_key()` methods
- Migration script `scripts/migrate-api-keys.py` for existing keys
- Updated `setup.sh` to generate hashed keys
- `bcrypt==4.1.2` dependency added to requirements.txt

### Added - High Priority Testing
- `pytest.ini` with coverage configuration (60% threshold)
- `tests/conftest.py` with shared fixtures (test_app, client, mock_ollama, mock_comfyui)
- Integration test suite in `tests/integration/test_full_workflow.py`
- Test markers: `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.security`
- `--run-integration` flag for integration tests

### Added - Code Quality
- `pyproject.toml` with Black, isort, and coverage configuration
- `.pre-commit-config.yaml` with automated hooks (black, isort, flake8, mypy)
- Line length standard: 120 characters
- Python version: 3.11

### Added - Documentation
- `docs/CRITICAL_FIXES_IMPLEMENTED.md` - Comprehensive critical issues documentation
- `CHANGELOG.md` - Version history tracking
- Enhanced docstrings across all routers
- API versioning in FastAPI metadata (v3.4)

### Changed
- Refactored `backend/main.py` from 1,163 to 154 lines (87% reduction)
- Updated security module to use bcrypt hashing
- Enhanced rate limiting to use API key hash as bucket ID
- Improved CI/CD with parallel job execution
- Updated version number from 3.3 to 3.4

### Fixed
- Security vulnerability: Plaintext API key storage
- Code maintainability: Oversized main.py file
- Missing CI/CD automation
- No test configuration or integration tests
- Repository hygiene: Missing .gitignore

### Security
- API keys now hashed with bcrypt (work factor 12, 4096 iterations)
- Constant-time comparison using `bcrypt.checkpw()`
- Per-API-key rate limiting in production mode
- TruffleHog secret scanning in CI/CD

## [3.3.0] - 2024-10-06

### Added
- Knowledge base administration endpoints
- Batch sprite generation from CSV
- Style preset system
- Regeneration with attempt tracking
- Prometheus metrics endpoint
- Structured JSON logging

### Changed
- Switched to local Ollama instance (from container)
- Enhanced error handling with retry logic

### Fixed
- Memory leak in conversation history
- Validation error handling

## [3.2.0] - 2024-10-04

### Added
- Security module with API key authentication
- Rate limiting (token bucket algorithm)
- Graceful degradation for service failures
- Circuit breakers for Ollama and ComfyUI

### Changed
- Improved logging with structured output
- Enhanced health check endpoint

## [3.1.0] - 2024-10-01

### Added
- PM Agent with Ollama integration
- ComfyUI sprite generation
- FAISS knowledge base
- GBStudio project manipulation
- Basic web interface

### Initial Release
- Core sprite generation workflow
- Docker containerization
- FastAPI backend
- Vanilla JavaScript frontend

---

[3.4.0]: https://github.com/yourorg/BSPM-UNIFIED/compare/v3.3.0...v3.4.0
[3.3.0]: https://github.com/yourorg/BSPM-UNIFIED/compare/v3.2.0...v3.3.0
[3.2.0]: https://github.com/yourorg/BSPM-UNIFIED/compare/v3.1.0...v3.2.0
[3.1.0]: https://github.com/yourorg/BSPM-UNIFIED/releases/tag/v3.1.0
