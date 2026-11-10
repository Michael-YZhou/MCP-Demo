# MCP Demo: News Sentiment Pipeline

A small [Model Context Protocol](https://modelcontextprotocol.io) (MCP) demo. An LLM-driven client connects to an MCP server that can search the news, analyze sentiment, and email a report. You ask in natural language, and the LLM plans which tools to call and in what order.

## How it works

```
 you ──► client.py ──(1) plan──► LLM (DashScope / Qwen)
            │
            │ (2) run tools over MCP stdio
            ▼
        server.py ──► search_google_news ──► Serper API
                  ──► analyze_sentiment  ──► LLM
                  ──► send_email_with_attachment ──► SMTP
            │
            │ (3) tool results
            ▼
         client.py ──(4) final answer──► LLM ──► you
```

1. **Plan.** The client sends your request and the list of available tools to the LLM. The LLM replies with a JSON plan: an ordered list of `{name, arguments}`.
2. **Execute.** The client starts `server.py` as a subprocess and calls each tool over MCP stdio. A later step can reference an earlier tool's output with a `{{tool_name}}` placeholder.
3. **Answer.** The tool results go back to the LLM, which writes the final reply.

### Tools (`src/cmp_demo/server.py`)

| Tool | What it does | Output |
|---|---|---|
| `search_google_news(keyword)` | Top 5 news results from the [Serper](https://serper.dev) Google News API | `google_news/*.json` |
| `analyze_sentiment(text, filename)` | LLM sentiment analysis of the given text | `sentiment_reports/<filename>.md` |
| `send_email_with_attachment(to, subject, body, filename)` | Emails a report over SMTP (SSL) | — |

The client also saves every conversation to `llm_outputs/*.txt`. Output folders are created in the directory you run from, and all of them are gitignored.

Prompts and console output are in Chinese.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.13+ (uv installs it automatically if it's missing)
- A DashScope API key (Alibaba Cloud Model Studio), or any OpenAI-compatible endpoint
- A Serper API key, for news search
- An SMTP account, for email. Many providers require an app password or authorization code instead of your login password

## Setup

```sh
git clone git@github.com:Michael-YZhou/MCP-Demo.git
cd MCP-Demo
uv sync                    # creates .venv and installs dependencies
cp .env.example .env       # then fill in your keys
```

`.env` variables:

| Variable | Purpose |
|---|---|
| `DASHSCOPE_API_KEY` | LLM API key |
| `BASE_URL` | OpenAI-compatible endpoint, e.g. `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `MODEL` | Model name, e.g. `qwen-plus` |
| `SERPER_API_KEY` | Serper news search key |
| `SMTP_SERVER`, `SMTP_PORT` | SMTP host and SSL port (default `465`) |
| `EMAIL_USER`, `EMAIL_PASS` | Sender account and password or app password |
| `LLM_PROVIDER` | Reserved for a future backend switch; not used yet |

`.env` holds secrets and is gitignored. Never commit it.

## Usage

Run from the project root:

```sh
uv run python src/cmp_demo/client.py
```

The client starts the server itself and lists the available tools. Then type a request, for example:

```
你: 分析一下小米su7近期的热点新闻，并发送邮件给 you@example.com
```

The client searches the news, writes a sentiment report to `sentiment_reports/`, and emails it as an attachment. Type `quit` to exit.

## Development

```sh
uv run pytest              # run the test suite
uv add <pkg>               # add a dependency
uv add --dev <pkg>         # add a dev dependency
```

The tests in `tests/test_client.py` swap the LLM and the MCP session for small fake objects. They make no network calls and start no server.

`mcp` is pinned to `<2` because the code uses the v1 `FastMCP` API.

## Project layout

```
.
├── src/cmp_demo/
│   ├── server.py        # MCP server with the three tools
│   ├── client.py        # LLM-planned MCP client (interactive chat loop)
│   ├── main.py          # placeholder
│   └── __init__.py      # package entry point (placeholder)
├── tests/
│   └── test_client.py
├── .env.example         # template for .env
├── pyproject.toml
└── uv.lock
```

## Future improvements

### Use an async OpenAI client in the tools

`analyze_sentiment` is an `async` tool but calls the synchronous `OpenAI` client. While it waits for the LLM, which often takes several seconds, the server's event loop is blocked. During that time the server can't run other tools, answer pings, or handle cancellations. `client.py` does the same in its planning and final-answer calls.

This is harmless today: there is one client over stdio, and tools run one at a time. It becomes a real bottleneck if the server ever serves several clients (SSE/HTTP transport), runs tools in parallel, or reports progress.

The change is small: switch to `AsyncOpenAI`, `await` the call, and create the client once instead of on every call, so its connection pool is reused.

```python
from openai import AsyncOpenAI

llm = AsyncOpenAI(api_key=os.getenv("DASHSCOPE_API_KEY"), base_url=os.getenv("BASE_URL"))

@mcp.tool()
async def analyze_sentiment(text: str, filename: str) -> str:
    ...
    response = await llm.chat.completions.create(model=os.getenv("MODEL"), messages=[...])
```

Related changes:
- `send_email_with_attachment` uses blocking `smtplib`. Run it with `await asyncio.to_thread(...)`, or switch to `aiosmtplib`.
- If `client.py` switches too, the fake `create` in `tests/test_client.py` must become `async def`.

### Other ideas

- **Provider switch.** Read `LLM_PROVIDER` and add an Ollama backend for local models.
- **Entry point.** Make `uv run cmp-demo` start the client, instead of the placeholder `main()`.
- **Server tests.** Add tests for `server.py`, with the Serper, LLM, and SMTP calls faked.
- **mcp 2.x.** Migrate from `FastMCP` to `MCPServer` and lift the `mcp<2` pin.
