"""Tests for cmp_demo.client.MCPClient.

The LLM and the MCP session are replaced by small fakes, so these tests
make no network calls and start no server process.
"""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cmp_demo import client as client_module
from cmp_demo.client import MCPClient

TOOL_SCHEMAS = {
    "search_google_news": {
        "type": "object",
        "properties": {"keyword": {"type": "string"}},
        "required": ["keyword"],
    },
    "analyze_sentiment": {
        "type": "object",
        "properties": {"text": {"type": "string"}, "filename": {"type": "string"}},
        "required": ["text", "filename"],
    },
    "send_email_with_attachment": {
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "filename": {"type": "string"},
        },
        "required": ["to", "subject", "body", "filename"],
    },
}


class FakeCompletions:
    """Stands in for OpenAI().chat.completions; replies with canned contents."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.replies.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class FakeSession:
    """Stands in for mcp.ClientSession; records tool calls."""

    def __init__(self):
        self.tool_calls = []

    async def list_tools(self):
        return SimpleNamespace(
            tools=[
                SimpleNamespace(name=name, description=f"{name} tool", inputSchema=schema)
                for name, schema in TOOL_SCHEMAS.items()
            ]
        )

    async def call_tool(self, name, arguments):
        self.tool_calls.append((name, dict(arguments)))
        return SimpleNamespace(content=[SimpleNamespace(text=f"{name} result")])


@pytest.fixture
def make_client(monkeypatch, tmp_path):
    """Build an MCPClient wired to fakes, writing outputs into tmp_path."""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)

    def _make(replies):
        c = MCPClient()
        c.client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(replies)))
        c.session = FakeSession()
        return c

    return _make


def test_plan_tool_usage_parses_plan_wrapped_in_json_code_fence(make_client):
    plan = [{"name": "search_google_news", "arguments": {"keyword": "小米su7"}}]
    c = make_client([f"```json\n{json.dumps(plan, ensure_ascii=False)}\n```"])

    result = asyncio.run(c.plan_tool_usage("搜索小米su7", tools=[]))

    assert result == plan


def test_tools_sent_to_llm_use_openai_parameters_key(make_client):
    c = make_client(["[]", "final answer"])

    asyncio.run(c.process_query("搜索小米su7"))

    sent_tools = c.client.chat.completions.calls[0]["tools"]
    for tool in sent_tools:
        function = tool["function"]
        assert "input_schema" not in function
        assert function["parameters"] == TOOL_SCHEMAS[function["name"]]


def test_email_attaches_same_report_file_that_analysis_wrote(make_client):
    plan = [
        {"name": "analyze_sentiment", "arguments": {"text": "news"}},
        {
            "name": "send_email_with_attachment",
            "arguments": {"to": "a@example.com", "subject": "s", "body": "b"},
        },
    ]
    c = make_client([json.dumps(plan), "final answer"])

    asyncio.run(c.process_query("分析小米su7"))

    calls = dict(c.session.tool_calls)
    report = calls["analyze_sentiment"]["filename"]
    assert report.startswith("sentiment_") and report.endswith(".md")
    assert calls["send_email_with_attachment"]["filename"] == report
    assert "attachment_path" not in calls["send_email_with_attachment"]


def test_final_llm_call_has_no_orphan_tool_messages(make_client):
    """OpenAI-compatible APIs reject a 'tool' message that does not answer
    a preceding assistant message's tool_calls."""
    plan = [{"name": "search_google_news", "arguments": {"keyword": "小米su7"}}]
    c = make_client([json.dumps(plan), "final answer"])

    asyncio.run(c.process_query("搜索小米su7"))

    final_messages = c.client.chat.completions.calls[-1]["messages"]
    assert all(m["role"] != "tool" for m in final_messages)
    assert "search_google_news result" in json.dumps(final_messages, ensure_ascii=False)


def test_default_server_path_is_server_py_next_to_client():
    path = Path(client_module.SERVER_SCRIPT_PATH)

    assert path == Path(client_module.__file__).with_name("server.py")
    assert path.is_file()


@pytest.mark.parametrize(
    ("query", "keyword"),
    [
        ("分析一下小米su7近期的热点新闻，并发送邮件", "小米su7近期"),
        ("分析关于小米su7的新闻", "小米su7"),
        ("查看一下最近小米的新闻", "小米"),
        ("搜索小米su7", "小米su7"),
        ("你好", "分析对象"),
    ],
)
def test_report_filename_uses_subject_keyword_without_filler_words(make_client, query, keyword):
    plan = [{"name": "analyze_sentiment", "arguments": {"text": "news"}}]
    c = make_client([json.dumps(plan), "final answer"])

    asyncio.run(c.process_query(query))

    filename = dict(c.session.tool_calls)["analyze_sentiment"]["filename"]
    assert filename.startswith(f"sentiment_{keyword}_")
