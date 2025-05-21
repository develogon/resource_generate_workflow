import pytest
from unittest.mock import patch, MagicMock, mock_open

from core.content_generator import ContentGenerator
from tests.fixtures.sample_content_generator import SAMPLE_TEMPLATE, SAMPLE_CONTEXT, SAMPLE_GENERATED_CONTENT


class TestContentGenerator:
    """コンテンツジェネレータの基底クラステスト"""

    @pytest.fixture
    def mock_claude_service(self):
        """モックClaudeサービス"""
        mock = MagicMock()
        mock.generate_content.return_value = {
            "content": SAMPLE_GENERATED_CONTENT
        }
        return mock

    @pytest.fixture
    def content_generator(self, mock_claude_service):
        """ContentGeneratorインスタンス"""
        file_manager = MagicMock()
        generator = ContentGenerator(claude_service=mock_claude_service, file_manager=file_manager)
        return generator

    def test_generate(self, content_generator, mock_claude_service):
        """コンテンツ生成のテスト"""
        # テスト用入力データ
        input_data = {
            "template_path": "templates/test_template.md",
            "context": SAMPLE_CONTEXT
        }
        
        # テンプレート読み込みのモック
        with patch('builtins.open', mock_open(read_data=SAMPLE_TEMPLATE)):
            # generate実行
            result = content_generator.generate(input_data)
            
            # Claude APIが呼ばれたことを確認
            mock_claude_service.generate_content.assert_called_once()
            
            # 結果の検証
            assert "# サンプルタイトル" in result
            assert "## 概要" in result
            assert "これはサンプル概要です。" in result
            assert "言語: Go" in result

    def test_generate_with_system_prompt(self, content_generator, mock_claude_service):
        """システムプロンプト付きコンテンツ生成のテスト"""
        # テスト用入力データ
        input_data = {
            "template_path": "templates/test_template.md",
            "context": SAMPLE_CONTEXT,
            "system_prompt": "あなたは技術記事専門のAIアシスタントです。"
        }
        
        # テンプレート読み込みのモック
        content_generator.file_manager.read_content.return_value = SAMPLE_TEMPLATE
        
        # generate実行
        result = content_generator.generate(input_data)
        
        # Claude APIが正しいパラメータで呼ばれたことを確認
        mock_claude_service.generate_content.assert_called_once()
        call_args = mock_claude_service.generate_content.call_args
        
        # 引数の検証
        assert call_args[0][0] is not None  # プロンプト
        assert call_args[0][1] == []  # 画像（デフォルト空リスト）
        assert call_args[0][2] == "あなたは技術記事専門のAIアシスタントです。"  # システムプロンプト
        
        # 結果の検証
        assert "# サンプルタイトル" in result
        assert "## 概要" in result
        assert "これはサンプル概要です。" in result
        assert "言語: Go" in result

    def test_format_output(self, content_generator):
        """出力フォーマットのテスト"""
        raw_content = SAMPLE_GENERATED_CONTENT
        
        # フォーマット実行
        formatted = content_generator.format_output(raw_content)
        
        # 結果の検証（基底クラスでは変更なし）
        assert formatted == raw_content

    def test_validate_content(self, content_generator):
        """コンテンツ検証のテスト"""
        # 有効な内容
        valid_content = SAMPLE_GENERATED_CONTENT
        assert content_generator.validate_content(valid_content) is True
        
        # 無効な内容（空文字列）
        assert content_generator.validate_content("") is False
        
        # 無効な内容（Noneオブジェクト）
        assert content_generator.validate_content(None) is False

    def test_optimize_prompt(self, content_generator):
        """プロンプト最適化のテスト"""
        # テンプレートと変数
        template = SAMPLE_TEMPLATE
        context = SAMPLE_CONTEXT
        
        # 最適化実行
        optimized = content_generator.optimize_prompt(template, context)
        
        # 変数が置換されていることを確認
        assert "# サンプルタイトル" in optimized
        assert "## 概要" in optimized
        assert "これはサンプル概要です。" in optimized
        assert "言語: Go" in optimized
        assert "難易度: 中級" in optimized
        assert "ここに本文が入ります。" in optimized
        
        # テンプレート変数記法が残っていないことを確認
        assert "{{" not in optimized
        assert "}}" not in optimized

    def test_subclass_implementation(self):
        """サブクラス実装のテスト"""
        # モックサービス
        mock_claude = MagicMock()
        mock_file_manager = MagicMock()
        
        # ContentGeneratorのサブクラス定義
        class TestGenerator(ContentGenerator):
            def format_output(self, raw_content):
                return f"Formatted: {raw_content}"
            
            def validate_content(self, content):
                return "Formatted" in content
        
        # サブクラスのインスタンス生成
        generator = TestGenerator(claude_service=mock_claude, file_manager=mock_file_manager)
        
        # オーバーライドメソッドのテスト
        assert generator.format_output("test") == "Formatted: test"
        assert generator.validate_content("Formatted: test") is True
        assert generator.validate_content("test") is False 