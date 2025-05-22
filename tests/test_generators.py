import pytest
from unittest.mock import AsyncMock

pytest.importorskip("app.generators.article", reason="Generators not yet implemented")

from app.generators.article import ArticleGenerator
from app.generators.script import ScriptGenerator
from app.generators.script_json import ScriptJsonGenerator
from app.generators.tweet import TweetGenerator
from app.generators.description import DescriptionGenerator
from app.generators.thumbnail import ThumbnailGenerator


@pytest.mark.asyncio
async def test_article_generator_calls_api(monkeypatch):
    gen = ArticleGenerator()
    mock_call_api = AsyncMock(return_value={"content": "# Article\ntext"})
    monkeypatch.setattr(gen, "_call_api", mock_call_api, raising=False)

    result = await gen.generate({"structure": {}, "section_content": "foo"})
    assert "Article" in result
    mock_call_api.assert_awaited()


@pytest.mark.asyncio
async def test_script_generator_process_response(monkeypatch):
    gen = ScriptGenerator()
    mock_call_api = AsyncMock(return_value={"content": "# Script\ntext"})
    monkeypatch.setattr(gen, "_call_api", mock_call_api, raising=False)

    result = await gen.generate({"structure": {}, "article": "foo"})
    assert "Script" in result


def test_tweet_generator_returns_list(monkeypatch):
    gen = TweetGenerator()
    monkeypatch.setattr(gen, "_call_api", lambda *a, **kw: {"tweets": ["t1", "t2"]}, raising=False)
    tweets = gen.generate_tweets({}, "foo")
    assert isinstance(tweets, list) and tweets


@pytest.mark.asyncio
async def test_script_json_generator_returns_dict(monkeypatch):
    gen = ScriptJsonGenerator()
    mock_call_api = AsyncMock(return_value={"content": '{"scenes": [{"text": "scene1"}]}'})
    monkeypatch.setattr(gen, "_call_api", mock_call_api, raising=False)

    result = await gen.generate({"structure": {}, "script": "# Script\nfoo"})
    assert isinstance(result, dict)
    assert "scenes" in result


@pytest.mark.asyncio
async def test_description_generator_process_response(monkeypatch):
    gen = DescriptionGenerator()
    mock_call_api = AsyncMock(return_value={"content": "# Description\ntext"})
    monkeypatch.setattr(gen, "_call_api", mock_call_api, raising=False)

    result = await gen.generate({"structure_md": "# Structure", "article": "# Article"})
    assert "Description" in result


def test_thumbnail_generator_optimize_template(monkeypatch):
    gen = ThumbnailGenerator()
    monkeypatch.setattr(gen, "_call_optimize_api", lambda *a, **kw: "optimized_yaml", raising=False)
    result = gen.optimize_template("yaml: template", "description")
    assert result == "optimized_yaml"


def test_thumbnail_generator_generate_image(monkeypatch):
    gen = ThumbnailGenerator()
    monkeypatch.setattr(gen, "_call_image_api", lambda *a, **kw: b"image_data", raising=False)
    result = gen.generate_image("yaml_prompt")
    assert isinstance(result, bytes)
    assert result == b"image_data"


def test_thumbnail_generator_log_usage(monkeypatch):
    gen = ThumbnailGenerator()
    # Mock a logger or metrics tracker if needed
    monkeypatch.setattr(gen, "_log", lambda *a, **kw: None, raising=False)
    
    # This should not raise an exception
    gen.log_usage({"model": "gpt-4o", "tokens": 100, "quality": "high"})
    assert True  # If we got here, the test passed 