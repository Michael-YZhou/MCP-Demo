# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Early-stage scaffold created with `uv init --package`. Python 3.13+ (pinned in `.python-version`), built with the `uv_build` backend. The GitHub repo is `Michael-YZhou/MCP-Demo`, so the planned client/server pair is an MCP demo backed by an LLM provider.

Not set up yet: runtime dependencies (`dependencies = []`), `uv.lock`, tests, linter, and formatter. Update this file once they are added. The first `uv sync` creates `uv.lock`; commit it.

## Commands

Use `uv` for everything:

- `uv sync`: create `.venv` and install the package in editable mode
- `uv run cmp-demo`: run the console entry point (`cmp_demo:main` in `src/cmp_demo/__init__.py`)
- `uv add <pkg>` / `uv add --dev <pkg>`: add dependencies (this updates `pyproject.toml` and `uv.lock`)
- `uv build`: build the sdist and wheel into `dist/`

## Layout

- `src/` layout: the importable package is `src/cmp_demo/`.
- `server.py` and `client.py` are empty placeholders. Nothing is implemented yet, and there is no wiring between these modules and `main()`, which only prints a greeting.

## Configuration

- Configuration comes from environment variables in `.env` at the project root. `.env` is gitignored and holds real secrets: never commit it or print its values.
- `.env.example` is the committed template. When you add, rename, or remove a variable, update `.env.example` in the same change, using placeholder values only.
- Current variables:
  - `LLM_PROVIDER`: backend selector, `dashscope` or `ollama`
  - `DASHSCOPE_BASE_URL`, `DASHSCOPE_API_KEY`, `DASHSCOPE_MODEL`: DashScope (OpenAI-compatible endpoint) settings
- There are no Ollama variables yet. Add them to both files when the `ollama` backend is implemented.
- Nothing loads `.env` yet. Either add `python-dotenv`, or run with `uv run --env-file .env cmp-demo`.

## Git

- The default branch is `main`, and `origin` is `git@github.com:Michael-YZhou/MCP-Demo.git` (SSH).
- `.gitignore` also excludes `.idea/` and `.DS_Store`.
