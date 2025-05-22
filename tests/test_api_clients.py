import pytest

pytest.importorskip("app.clients.claude", reason="Clients not yet implemented")

from app.clients.claude import ClaudeAPIClient
from app.clients.openai import OpenAIClient
from app.clients.github import GitHubClient
from app.clients.s3 import S3Client
from app.clients.slack import SlackClient


def test_claude_prepare_request():
    client = ClaudeAPIClient()
    req = client.prepare_request("hello")
    assert isinstance(req, dict)
    assert "prompt" in req or req  # minimal check


def test_openai_optimize_template(monkeypatch):
    client = OpenAIClient()
    monkeypatch.setattr(client, "_call_gpt", lambda *a, **kw: "optimized", raising=False)
    result = client.optimize_template("yaml: x", "desc")
    assert result == "optimized"


def test_github_push_file(monkeypatch):
    client = GitHubClient()
    monkeypatch.setattr(client, "_api_call", lambda *a, **kw: {"url": "https://github"}, raising=False)
    url = client.push_file("foo.md", "text", "msg")
    assert "http" in url 


def test_s3_upload_file(monkeypatch):
    client = S3Client()
    monkeypatch.setattr(client, "_upload_to_s3", lambda *a, **kw: {"url": "https://s3.example.com/file"}, raising=False)
    url = client.upload_file(b"data", "key", "image/png")
    assert isinstance(url, str)
    assert "http" in url


def test_s3_get_public_url():
    client = S3Client()
    url = client.get_public_url("images/test.png")
    assert isinstance(url, str)
    assert "images/test.png" in url


def test_slack_send_notification(monkeypatch):
    client = SlackClient()
    monkeypatch.setattr(client, "_send_message", lambda *a, **kw: {"ok": True}, raising=False)
    result = client.send_notification("Test message")
    assert result or result == {"ok": True}


def test_slack_send_error_alert(monkeypatch):
    client = SlackClient()
    monkeypatch.setattr(client, "_send_message", lambda *a, **kw: {"ok": True}, raising=False)
    result = client.send_error_alert("Error occurred", {"task": "test_task"})
    assert result or result == {"ok": True} 