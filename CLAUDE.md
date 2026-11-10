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

The code was imported from another project (`mcp-project`, originally run on Windows). Packaging and dependencies are integrated. The client finds `server.py` next to itself (`SERVER_SCRIPT_PATH`) and launches it with `sys.executable`, so it works from any CWD. The MCP stdio handshake is verified, but no end-to-end run with real LLM, Serper, or SMTP calls has been done yet. Remaining work:

- **No real entry point.** `cmp-demo` (`cmp_demo:main` in `__init__.py`) only prints a greeting. `main.py` is a leftover hello-world stub from the old project.
- **`mcp` is pinned to `<2`.** The code uses the v1 API (`from mcp.server.fastmcp import FastMCP`). In mcp 2.x, FastMCP was renamed to `MCPServer` (`mcp.server.mcpserver`). Migrate the code before lifting the pin.
- No linter or formatter is set up.
- `client.py` and `server.py` use CRLF line endings, carried over from Windows. Keep them CRLF when editing, so diffs show only real changes, or normalize both files in a separate commit.

## Client behaviour worth knowing

- The client does not use native OpenAI tool calling. The LLM returns a JSON plan in plain text, and the client runs it. Tool results go back to the LLM in a `user` message, never a `role: "tool"` message: OpenAI-compatible APIs reject a `tool` message that has no matching assistant `tool_calls`.
- The client fills in `filename` for both `analyze_sentiment` and `send_email_with_attachment` when the plan omits it, so the email attaches the report that the analysis just wrote.

- The report filename comes from a keyword regex in `process_query`. It takes the text after a verb (关于/分析/查询/搜索/查看), skips the filler words 一下, 关于, and 最近/近期 right after the verb, and stops at 的, whitespace, or punctuation. A trailing time word stays: "分析一下小米su7近期的…" yields `小米su7近期`.

## Known issues in the code
- The tools use the synchronous `OpenAI` client inside `async` functions, which blocks the event loop.
- `LLM_PROVIDER` (`dashscope | ollama`) is not read anywhere, and no Ollama backend exists.

## Commands

Use `uv` for everything, and run it from the project root (not from `src/cmp_demo/`):

- `uv sync`: create `.venv` and install the package in editable mode
- `uv add <pkg>` / `uv add --dev <pkg>`: add dependencies (this updates `pyproject.toml` and `uv.lock`)
- `uv run cmp-demo`: the console entry point (currently prints a greeting only)
- `uv run python src/cmp_demo/client.py`: the interactive client. It starts the server itself
- `uv run pytest`: run the tests. `uv run pytest tests/test_client.py::<test_name>` runs a single test
- `uv build`: build the sdist and wheel into `dist/`

Dependencies are `mcp` (`>=1.6.0,<2`), `openai`, `python-dotenv`, and `httpx`, with `pytest` in the `dev` group. They are locked in the root `uv.lock`; commit it.

## Tests

`tests/test_client.py` tests `MCPClient` with fake objects in place of the OpenAI client (`client.chat.completions.create`) and the MCP `ClientSession` (`list_tools`, `call_tool`). The tests make no network calls and start no server. They `chdir` into a temp directory, so output files never land in the repo. Async methods are driven with `asyncio.run`, so `pytest-asyncio` isn't needed. `server.py` has no tests yet.

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
