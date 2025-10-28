# Repository Guidelines

## Project Structure & Module Organization
- `app.py` is the Flask entry point; keep it lightweight and push new logic into blueprints or services.
- `core/` owns the application factory, scheduled jobs, and streaming helpers; extend `create_app` when wiring new subsystems.
- `routes/` splits UI and API traffic between `main.py` and `api.py`. Register extra blueprints here to keep routing explicit.
- `utils/` stores data access, caching, and sensor helpers. Keep raw device assets in `utils/data/` and share services through this package.
- `static/` and `templates/` pair the modern UI assets with Jinja templates. Mirror filenames when creating new views to ease maintenance.
- `config/` centralises environment switches and data factories for consistent configuration.

## Build, Test, and Development Commands
- `python -m venv .venv; ./.venv/Scripts/Activate.ps1` creates the Windows virtualenv and keeps dependencies isolated.
- `pip install -r requirements.txt` installs Flask, Redis, OpenCV, and numpy; rerun after editing factory or sensor modules.
- `python app.py` launches the dev server (port 5000, debug mode). Production paths include `./deploy.sh production up`, `docker-compose up`, or the manifests in `k8s-deployment.yaml`.
- `python -m pytest tests` (once suites exist) runs backend checks; scope with `pytest -k sensor` during focused development.

## Coding Style & Naming Conventions
- Follow PEP 8, 4-space indentation, and annotate public functions. Modules stay snake_case; classes use PascalCase; constants use CAPS.
- JavaScript in `static/js/` is ES6+. Export functions explicitly, prefer arrow functions for callbacks, and keep filenames kebab-case to match the existing bundle.
- Run `black .` and `flake8` before pushes. Front-end changes should pass `npx prettier --write static/js static/css` if Node tooling is installed.

## Testing Guidelines
- Target Pytest coverage for data ingestion, caching layers, and Flask routes. Name files after modules (`test_data_store.py`, `test_api.py`).
- Store fixtures under `tests/fixtures/` so sample CSV and image assets stay separate from `utils/data/`.
- Smoke-test the UI by visiting `/dashboard` with live or recorded sensor data. Capture regressions with lightweight scripts or manual checklists when automation is impractical.

## Commit & Pull Request Guidelines
- Recent commits are short, action-led summaries (e.g., `Fix dashboard CSV encoding`); keep each commit scoped to one behaviour change.
- Describe intent, risks, and verification in the PR body. Link related issues and attach screenshots or logs for UI, streaming, or performance changes.
- Confirm Pytest and lint checks before requesting review. Note any skipped tests, configuration toggles, or follow-up tasks directly in the PR.
