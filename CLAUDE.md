# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Early-stage scaffold created with `uv init --package`. Python 3.13+ (pinned in `.python-version`), built with the `uv_build` backend. No runtime dependencies, tests, linter, or formatter are configured yet. Update this file once they are added.

## Commands

Use `uv` for everything:

- `uv sync`: create `.venv` and install the package in editable mode
- `uv run cmp-demo`: run the console entry point (`cmp_demo:main` in `src/cmp_demo/__init__.py`)
- `uv add <pkg>` / `uv add --dev <pkg>`: add dependencies (this updates `pyproject.toml` and `uv.lock`)
- `uv build`: build the sdist and wheel into `dist/`

## Layout

- `src/` layout: the importable package is `src/cmp_demo/`.
- `server.py` and `client.py` are empty placeholders, so the project is set up for a client/server pair. Nothing is implemented yet, and there is no wiring between these modules and `main()`.
