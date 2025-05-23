import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.generators.script import ScriptGenerator
from src.generators.base import GenerationType, GenerationRequest, GenerationResult
from src.models import Content
from src.config import Config

# ... existing code ...

class TestScriptGenerator:
    """ScriptGenerator test class."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock config fixture."""
        config = MagicMock()
        # Mock workers config
        workers_mock = MagicMock()
        workers_mock.max_concurrent_tasks = 5
        config.workers = workers_mock
        return config
    
    @pytest.fixture
    def generator(self, mock_config):
        """Generator fixture."""
        return ScriptGenerator(mock_config)
    
    def test_get_generation_type(self, generator):
        """Test generation type."""
        assert generator.get_generation_type() == GenerationType.SCRIPT
    
    def test_get_prompt_template(self, generator):
        """Test prompt template."""
        template = generator.get_prompt_template()
        assert isinstance(template, str)
        assert len(template) > 0
    
    @pytest.mark.asyncio
    async def test_generate_success(self, generator):
        """Test successful script generation."""
        content = Content(
            id="test-1",
            title="テスト動画",
            content="テストコンテンツです。",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.SCRIPT,
            options={"title": "テスト動画"},
            context={}
        )
        
        result = await generator.generate(request)
        
        assert result.success is True
        assert result.content != ""
        assert result.generation_type == GenerationType.SCRIPT
        
        # JSON形式の確認
        try:
            script_data = json.loads(result.content)
            assert "title" in script_data
            assert "duration" in script_data
            assert "sections" in script_data
            assert isinstance(script_data["sections"], list)
        except json.JSONDecodeError:
            pytest.fail("Generated script is not valid JSON")
            
    @pytest.mark.asyncio
    async def test_generate_with_ai_client(self, generator):
        """Test generation with AI client."""
        # Mock AI client
        mock_ai_client = AsyncMock()
        mock_response = {
            "content": json.dumps({
                "title": "AI生成テスト動画",
                "duration": "3:00",
                "sections": [
                    {
                        "type": "introduction",
                        "duration": "30",
                        "script": "AI生成の導入部分です。",
                        "notes": "AI生成の演出ノート"
                    }
                ]
            })
        }
        mock_ai_client.generate.return_value = mock_response
        generator.set_ai_client(mock_ai_client)
        
        content = Content(
            id="test-2",
            title="AIテスト",
            content="AI生成テスト",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.SCRIPT,
            options={"title": "AIテスト"},
            context={}
        )
        
        result = await generator.generate(request)
        
        assert result.success is True
        script_data = json.loads(result.content)
        assert script_data["title"] == "AI生成テスト動画"
        mock_ai_client.generate.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_generate_ai_client_failure(self, generator):
        """Test generation when AI client fails."""
        # Mock AI client that fails
        mock_ai_client = AsyncMock()
        mock_ai_client.generate.side_effect = Exception("AI failure")
        generator.set_ai_client(mock_ai_client)
        
        content = Content(
            id="test-3",
            title="テスト",
            content="テスト",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.SCRIPT,
            options={"title": "テスト"},
            context={}
        )
        
        result = await generator.generate(request)
        
        # Should fallback to simulation
        assert result.success is True
        assert result.content != ""

# ... existing code ...

    def test_post_process_script_valid_json(self, generator):
        """Test post-processing valid JSON script."""
        valid_script = json.dumps({
            "title": "テスト動画",
            "duration": "2:00",
            "sections": [
                {
                    "type": "introduction",
                    "script": "導入部分"
                }
            ]
        })
        
        content = Content(
            id="test-4",
            title="test",
            content="test",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.SCRIPT,
            options={},
            context={}
        )
        
        result = generator._post_process_script(valid_script, request)
        
        # Should return valid JSON
        parsed = json.loads(result)
        assert parsed["title"] == "テスト動画"
        
    def test_post_process_script_json_block(self, generator):
        """Test post-processing script with JSON code block."""
        script_with_block = '''```json
{
    "title": "テスト動画",
    "duration": "2:00",
    "sections": []
}
```'''
        
        content = Content(
            id="test-5",
            title="test",
            content="test",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.SCRIPT,
            options={},
            context={}
        )
        
        result = generator._post_process_script(script_with_block, request)
        
        # Should extract JSON from code block
        parsed = json.loads(result)
        assert parsed["title"] == "テスト動画"
        
    def test_post_process_script_invalid_json(self, generator):
        """Test post-processing invalid JSON."""
        invalid_json = "not valid json content"
        
        content = Content(
            id="test-6",
            title="test",
            content="test",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.SCRIPT,
            options={},
            context={}
        )
        
        result = generator._post_process_script(invalid_json, request)
        
        # Should return original content
        assert result == invalid_json

# ... existing code ...

    @pytest.mark.asyncio
    async def test_generate_invalid_request(self, generator):
        """Test generation with invalid request."""
        # Test with None content
        request = GenerationRequest(
            content=None,
            generation_type=GenerationType.SCRIPT,
            options={},
            context={}
        )
        
        result = await generator.generate(request)
        assert result.success is False
        
    @pytest.mark.asyncio
    async def test_generate_wrong_type(self, generator):
        """Test generation with wrong type."""
        content = Content(
            id="test-7",
            title="test",
            content="test",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.ARTICLE,  # Wrong type
            options={},
            context={}
        )
        
        result = await generator.generate(request)
        assert result.success is False
        
    def test_prompt_building(self, generator):
        """Test prompt building."""
        content = Content(
            id="test-8",
            title="テストタイトル",
            content="テストコンテンツ",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.SCRIPT,
            options={"title": "テストタイトル"},
            context={}
        )
        
        prompt = generator.build_prompt(request)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
    def test_metadata_extraction(self, generator):
        """Test metadata extraction."""
        content = Content(
            id="test-9",
            title="test content",
            content="test content",
            metadata={}
        )
        request = GenerationRequest(
            content=content,
            generation_type=GenerationType.SCRIPT,
            options={"test_option": True},
            context={"test_context": "value"}
        )
        
        result = "generated script"
        metadata = generator.extract_metadata(request, result)
        
        assert metadata["generation_type"] == "script"
        assert metadata["source_title"] == "test content"
        assert "word_count" in metadata
        assert "char_count" in metadata
        assert "generated_at" in metadata