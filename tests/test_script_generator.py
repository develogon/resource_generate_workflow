import pytest
from unittest.mock import patch, MagicMock, mock_open

from generators.script import ScriptGenerator
from tests.fixtures.sample_script_data import (
    SAMPLE_SCRIPT_INPUT,
    SAMPLE_SCRIPT_TEMPLATE,
    SAMPLE_GENERATED_SCRIPT
)


class TestScriptGenerator:
    """スクリプト生成器のテスト"""

    @pytest.fixture
    def mock_claude_service(self):
        """モックClaudeサービス"""
        mock = MagicMock()
        mock.generate_content.return_value = {
            "content": SAMPLE_GENERATED_SCRIPT
        }
        return mock

    @pytest.fixture
    def script_generator(self, mock_claude_service):
        """ScriptGeneratorインスタンス"""
        file_manager = MagicMock()
        return ScriptGenerator(claude_service=mock_claude_service, file_manager=file_manager)

    def test_generate(self, script_generator, mock_claude_service):
        """スクリプト生成のテスト"""
        # テスト用入力データ
        input_data = SAMPLE_SCRIPT_INPUT
        
        # テンプレート読み込みのモック
        with patch('builtins.open', mock_open(read_data=SAMPLE_SCRIPT_TEMPLATE)):
            # スクリプト生成実行
            result = script_generator.generate(input_data)
            
            # Claude APIが呼ばれたことを確認
            mock_claude_service.generate_content.assert_called_once()
            
            # 結果の検証
            assert "# Goの並行処理 スクリプト" in result
            assert "## ナレーション" in result
            assert "今回はGoの並行処理について解説します。" in result
            assert "ナレーター: 「Goの並行処理の特徴は" in result

    def test_format_output(self, script_generator):
        """出力フォーマットのテスト"""
        # 入力スクリプト
        raw_script = """
        # テストスクリプト
        
        ## ナレーション
        
        これはテストナレーションです。
        
        ## スクリプト
        
        ナレーター: 「テストスクリプトの始まりです。」
        
        (コード表示)
        
        ナレーター: 「テストスクリプトの終わりです。」
        """
        
        # フォーマット実行
        formatted = script_generator.format_output(raw_script)
        
        # スクリプト構造が保持されていることを確認
        assert "# テストスクリプト" in formatted
        assert "## ナレーション" in formatted
        assert "## スクリプト" in formatted
        assert "ナレーター: 「テストスクリプトの始まりです。」" in formatted
        
        # 無効なスクリプト形式
        invalid_script = "# タイトルのみ"
        formatted_invalid = script_generator.format_output(invalid_script)
        assert formatted_invalid == invalid_script

    def test_validate_content(self, script_generator):
        """スクリプト検証のテスト"""
        # 有効なスクリプト
        valid_script = SAMPLE_GENERATED_SCRIPT
        assert script_generator.validate_content(valid_script) is True
        
        # 無効なスクリプト（空）
        assert script_generator.validate_content("") is False
        
        # 無効なスクリプト（ナレーション部分なし）
        invalid_script = "# タイトルのみのスクリプト"
        assert script_generator.validate_content(invalid_script) is False

    def test_structure_script(self, script_generator):
        """スクリプト構造化のテスト"""
        # 基本スクリプト
        basic_script = """
        # タイトル
        
        ## ナレーション
        
        これはナレーションです。
        
        ## スクリプト内容
        
        ナレーター: 「スクリプト内容です。」
        """
        
        # 構造化実行
        structured = script_generator.structure_script(basic_script)
        
        # 基本構造が保持されていることを確認
        assert "# タイトル" in structured
        assert "## ナレーション" in structured
        assert "## スクリプト内容" in structured
        
        # 短いスクリプト
        short_script = "# 短いスクリプト"
        structured_short = script_generator.structure_script(short_script)
        assert structured_short == short_script

    def test_optimize_prompt(self, script_generator):
        """プロンプト最適化のテスト"""
        # テンプレートと変数
        template = """
        # {{section_title}} スクリプト
        
        ## ナレーション
        
        今回は{{language}}の{{section_title}}について解説します。
        
        ## 内容
        
        {{content}}
        """
        
        context = {
            "section_title": "Goの並行処理",
            "language": "Go",
            "content": "Goの並行処理機能についての解説です。"
        }
        
        # 最適化実行
        optimized = script_generator.optimize_prompt(template, context)
        
        # 変数が置換されていることを確認
        assert "# Goの並行処理 スクリプト" in optimized
        assert "今回はGoのGoの並行処理について解説します。" in optimized
        assert "Goの並行処理機能についての解説です。" in optimized 