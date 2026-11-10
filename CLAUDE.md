# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An MCP demo: a news-sentiment pipeline with a FastMCP stdio server and an LLM-driven client. The LLM is DashScope (Qwen), reached through the `openai` SDK's OpenAI-compatible API. Code comments, prompts, and user-facing strings are in Chinese.

- `src/cmp_demo/server.py`: the `FastMCP("NewsServer")` stdio server, with three tools:
  - `search_google_news(keyword)`: Serper news API (`google.serper.dev/news`). Returns the top 5 results and saves them to `./google_news/*.json`.
  - `analyze_sentiment(text, filename)`: LLM sentiment analysis. Writes a Markdown report to `./sentiment_reports/<filename>` and returns its path.
  - `send_email_with_attachment(to, subject, body, filename)`: SMTP over SSL. Attaches `./sentiment_reports/<filename>`.
- `src/cmp_demo/client.py`: `MCPClient`, an interactive chat loop. It starts the server as a subprocess over stdio. For each query, `process_query`:
  1. derives a report filename from the query with a regex, then appends `[md_filename=…] [md_path=…]` to the query
  2. calls `plan_tool_usage`, which asks the LLM for a JSON array of `{name, arguments}`. An argument value written as `{{tool_name}}` is replaced with that earlier tool's text output
  3. runs the tools in order, then makes a final LLM call over the tool results
  4. saves the transcript to `./llm_outputs/*.txt`
- All output directories are relative to the current working directory. The server subprocess inherits its CWD from the client. Run from the project root, so outputs land in `./google_news/`, `./sentiment_reports/`, and `./llm_outputs/` there. All three are gitignored.
- Keep runtime outputs out of `src/cmp_demo/`. `uv_build` packages every file in the module directory into the wheel, whether or not git ignores it.

## Project status

The code was imported from another project (`mcp-project`, originally run on Windows). Packaging and dependencies are now integrated. The client and server import and complete an MCP stdio handshake. Remaining work:

- **Hardcoded server path.** `client.main()` launches `D:\mcp-project\server.py`, so the interactive client can't start until that path is fixed.
- **No real entry point.** `cmp-demo` (`cmp_demo:main` in `__init__.py`) only prints a greeting. `main.py` is a leftover hello-world stub from the old project.
- **`mcp` is pinned to `<2`.** The code uses the v1 API (`from mcp.server.fastmcp import FastMCP`). In mcp 2.x, FastMCP was renamed to `MCPServer` (`mcp.server.mcpserver`). Migrate the code before lifting the pin.
- No tests, linter, or formatter are set up.

## Known bugs in the code

- `client.py` injects `attachment_path` for `send_email_with_attachment`, but that tool's parameter is `filename`, so the injection does nothing. The email step only works if the LLM supplies `filename` itself.
- The tool definitions sent to the LLM use the key `input_schema`. The OpenAI function-tool format expects `parameters`, so the model never sees the argument schemas.
- `plan_tool_usage` strips code fences with `r"```(?:json)?\\s*…\\s*```"`. In a raw string, `\\s` matches a literal backslash followed by `s`, so fenced JSON is never extracted, `json.loads` fails, and the plan comes back empty.
- The filename keyword regex captures too much. For example, "分析一下小米su7…" yields `一下小米su7近期`.
- The tools use the synchronous `OpenAI` client inside `async` functions, which blocks the event loop.
- `LLM_PROVIDER` (`dashscope | ollama`) is not read anywhere, and no Ollama backend exists.

## Commands

Use `uv` for everything, and run it from the project root (not from `src/cmp_demo/`):

- `uv sync`: create `.venv` and install the package in editable mode
- `uv add <pkg>` / `uv add --dev <pkg>`: add dependencies (this updates `pyproject.toml` and `uv.lock`)
- `uv run cmp-demo`: the console entry point (currently prints a greeting only)
- `uv run python src/cmp_demo/client.py`: the interactive client, after the hardcoded server path is fixed
- `uv build`: build the sdist and wheel into `dist/`

Dependencies are `mcp` (`>=1.6.0,<2`), `openai`, `python-dotenv`, and `httpx`. They are locked in the root `uv.lock`; commit it.

## Configuration

- Configuration comes from environment variables in `.env` at the project root. `.env` is gitignored and holds real secrets: never commit it or print its values. Both modules call `load_dotenv()` at import time.
- `.env.example` is the committed template. When you add, rename, or remove a variable, update `.env.example` in the same change, using placeholder values only.
- The code's variable names are the source of truth. `.env` and `.env.example` follow them:

| Variable | Used in | Purpose |
|---|---|---|
| `DASHSCOPE_API_KEY` | client, server | LLM API key |
| `BASE_URL` | client, server | OpenAI-compatible endpoint (DashScope) |
| `MODEL` | client, server | model name, e.g. `qwen-plus` |
| `SERPER_API_KEY` | server | Serper news search |
| `SMTP_SERVER`, `SMTP_PORT` (default 465), `EMAIL_USER`, `EMAIL_PASS` | server | sending email over SMTP SSL |
| `LLM_PROVIDER` | none yet | planned backend switch, `dashscope` or `ollama` |

## Git

- The default branch is `main`, and `origin` is `git@github.com:Michael-YZhou/MCP-Demo.git` (SSH).
- `.gitignore` also excludes `.env`, `.idea/`, `.DS_Store`, and the three runtime output directories.
