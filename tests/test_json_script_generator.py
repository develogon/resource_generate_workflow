import pytest
import json
from unittest.mock import patch, MagicMock, mock_open

from generators.json_script import JSONScriptGenerator
from tests.fixtures.sample_script_data import (
    SAMPLE_JSON_SCRIPT_INPUT,
    SAMPLE_GENERATED_JSON_SCRIPT
)


class TestJSONScriptGenerator:
    """JSONスクリプト生成器のテスト"""

    @pytest.fixture
    def mock_claude_service(self):
        """モックClaudeサービス"""
        mock = MagicMock()
        mock.generate_content.return_value = {
            "content": SAMPLE_GENERATED_JSON_SCRIPT
        }
        return mock

    @pytest.fixture
    def json_script_generator(self, mock_claude_service):
        """JSONScriptGeneratorインスタンス"""
        file_manager = MagicMock()
        return JSONScriptGenerator(claude_service=mock_claude_service, file_manager=file_manager)

    def test_generate(self, json_script_generator, mock_claude_service):
        """JSONスクリプト生成のテスト"""
        # テスト用入力データ
        input_data = SAMPLE_JSON_SCRIPT_INPUT
        
        # テンプレート読み込みのモック
        template_content = """
        # {{section_title}} - JSONスクリプト
        
        以下の内容から、{{section_title}}に関するJSONスクリプトを作成してください。
        
        内容:
        {{content}}
        
        言語: {{language}}
        """
        
        with patch('builtins.open', mock_open(read_data=template_content)):
            # JSONスクリプト生成実行
            result = json_script_generator.generate(input_data)
            
            # Claude APIが呼ばれたことを確認
            mock_claude_service.generate_content.assert_called_once()
            
            # 結果の検証
            assert "Goの並行処理" in result
            assert "duration" in result
            assert "scenes" in result
            assert "narration" in result

    def test_format_output(self, json_script_generator):
        """出力フォーマットのテスト"""
        # JSONテキスト
        json_text = SAMPLE_GENERATED_JSON_SCRIPT
        
        # フォーマット実行
        formatted = json_script_generator.format_output(json_text)
        
        # JSONが整形されていることを確認
        try:
            parsed = json.loads(formatted)
            assert parsed["title"] == "Goの並行処理"
            assert len(parsed["scenes"]) == 4
            assert parsed["scenes"][0]["type"] == "intro"
        except json.JSONDecodeError:
            pytest.fail("Formatted output is not valid JSON")
        
        # 無効なJSON
        invalid_json = "{ invalid json }"
        with pytest.raises(ValueError):
            json_script_generator.format_output(invalid_json)

    def test_validate_content(self, json_script_generator):
        """JSONスクリプト検証のテスト"""
        # 有効なJSONスクリプト
        valid_json = SAMPLE_GENERATED_JSON_SCRIPT
        assert json_script_generator.validate_content(valid_json) is True
        
        # 無効なJSON（空）
        assert json_script_generator.validate_content("") is False
        
        # 無効なJSON（シンタックスエラー）
        invalid_json = "{ invalid json }"
        assert json_script_generator.validate_content(invalid_json) is False
        
        # 必須フィールドがないJSON
        incomplete_json = """
        {
          "title": "テストタイトル"
        }
        """
        assert json_script_generator.validate_content(incomplete_json) is False

    def test_extract_json(self, json_script_generator):
        """JSONコンテンツ抽出のテスト"""
        # JSONを含むテキスト
        mixed_content = """
        # JSONスクリプト
        
        以下にJSONスクリプトを作成しました。
        
        ```json
        {
          "title": "テストタイトル",
          "duration": "00:05:00",
          "scenes": [
            {
              "type": "intro",
              "narration": "テスト導入",
              "duration": "00:01:00"
            }
          ]
        }
        ```
        
        以上です。
        """
        
        # JSON抽出
        extracted = json_script_generator.extract_json(mixed_content)
        
        # 抽出されたJSONの検証
        assert "title" in extracted
        assert "duration" in extracted
        assert "scenes" in extracted
        
        # JSONブロックがない場合
        no_json_content = "JSONブロックがないテキスト"
        with pytest.raises(ValueError):
            json_script_generator.extract_json(no_json_content)

    def test_modify_durations(self, json_script_generator):
        """継続時間調整のテスト"""
        # テスト用スクリプト
        script = {
            "title": "テストタイトル",
            "duration": "00:06:00",
            "scenes": [
                {"type": "intro", "duration": "00:01:00"},
                {"type": "explanation", "duration": "00:02:00"},
                {"type": "code_example", "duration": "00:02:00"},
                {"type": "conclusion", "duration": "00:01:00"}
            ]
        }
        
        # 継続時間調整
        modified = json_script_generator.modify_durations(script, target_total="00:05:00")
        
        # 総時間が調整されたことを確認
        assert modified["duration"] == "00:05:00"
        
        # 各シーンの時間が比例して調整されたことを確認
        assert modified["scenes"][0]["duration"] == "00:00:50"  # 約50秒
        assert modified["scenes"][1]["duration"] == "00:01:40"  # 約1分40秒
        assert modified["scenes"][2]["duration"] == "00:01:40"  # 約1分40秒
        assert modified["scenes"][3]["duration"] == "00:00:50"  # 約50秒