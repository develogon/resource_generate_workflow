import pytest
from unittest.mock import patch, MagicMock, mock_open

from generators.description import DescriptionGenerator


class TestDescriptionGenerator:
    """概要生成器のテスト"""

    @pytest.fixture
    def mock_claude_service(self):
        """モックClaudeサービス"""
        mock = MagicMock()
        mock.generate_content.return_value = {
            "content": """# Goプログラミング入門 - 概要

## 本書の概要

Goプログラミング入門は、Googleによって開発されたプログラミング言語であるGo言語（Golang）について包括的に解説する入門書です。
この書籍では、Goの基礎から応用まで順を追って解説し、実践的なプログラミングスキルを身につけることができます。

## 対象読者

- プログラミング初心者で、シンプルな言語から始めたい方
- 他のプログラミング言語経験者で、Goを学びたい方
- 並行処理や高性能なシステム開発に興味がある方

## 主な内容

1. **Goの基礎**: 変数、データ型、制御構造などの基本構文
2. **関数とパッケージ**: 関数定義、エラー処理、標準パッケージの使い方
3. **並行処理**: goroutineとchannelを使った効率的な並行プログラミング
4. **実践的な開発**: WebアプリケーションやAPIの開発手法

## 特徴

- 豊富なコード例とサンプルプロジェクト
- ステップバイステップの解説で初心者でも理解しやすい
- 実務で使える実践的なテクニックの紹介

この書籍を通じて、効率的で信頼性の高いアプリケーション開発に必要なGoの知識とスキルを習得できます。
"""
        }
        return mock

    @pytest.fixture
    def description_generator(self, mock_claude_service):
        """DescriptionGeneratorインスタンス"""
        file_manager = MagicMock()
        return DescriptionGenerator(claude_service=mock_claude_service, file_manager=file_manager)

    def test_generate(self, description_generator, mock_claude_service):
        """概要生成のテスト"""
        # テスト用入力データ
        input_data = {
            "title": "Goプログラミング入門",
            "structure_path": "path/to/structure.md",
            "template_path": "templates/description.md",
            "language": "Go"
        }
        
        # 構造ファイル読み込みのモック
        structure_content = """# Goプログラミング入門

## 第1章 Goの基礎
- 1.1 Goとは
- 1.2 開発環境のセットアップ

## 第2章 基本構文
- 2.1 変数と定数
- 2.2 制御構造
"""
        
        # テンプレート読み込みのモック
        template_content = """
        # {{title}} - 概要プロンプト
        
        以下の構造をもとに、{{title}}の概要を作成してください。
        
        {{structure}}
        
        言語: {{language}}
        """
        
        # テンプレートファイル読み込みのモック
        description_template = """
        ## 技術情報
        
        - 言語: {{language}}
        - バージョン: 最新
        """
        
        # 複数のファイル読み込みをモック
        mock_file_handles = [
            mock_open(read_data=structure_content).return_value,
            mock_open(read_data=template_content).return_value,
            mock_open(read_data=description_template).return_value
        ]
        mock_open_func = mock_open()
        mock_open_func.side_effect = mock_file_handles
        
        with patch('builtins.open', mock_open_func):
            # 概要生成実行
            result = description_generator.generate(input_data)
            
            # Claude APIが呼ばれたことを確認
            mock_claude_service.generate_content.assert_called_once()
            
            # 結果の検証
            assert "# Goプログラミング入門 - 概要" in result
            assert "## 本書の概要" in result
            assert "## 対象読者" in result
            assert "## 主な内容" in result
            assert "## 特徴" in result
            assert "## 技術情報" in result
            assert "- 言語: Go" in result

    def test_format_output(self, description_generator):
        """出力フォーマットのテスト"""
        # 生成された概要テキスト
        description_text = """# テスト概要

## セクション1

これはテストセクション1です。

## セクション2

これはテストセクション2です。
"""
        
        # フォーマット実行
        formatted = description_generator.format_output(description_text)
        
        # Markdown構造が保持されていることを確認
        assert "# テスト概要" in formatted
        assert "## セクション1" in formatted
        assert "## セクション2" in formatted
        assert "これはテストセクション1です。" in formatted
        assert "これはテストセクション2です。" in formatted

    def test_validate_content(self, description_generator):
        """概要検証のテスト"""
        # 有効な概要
        valid_description = """# テスト概要

## セクション1

これはテストセクション1です。

## セクション2

これはテストセクション2です。
"""
        assert description_generator.validate_content(valid_description) is True
        
        # 無効な概要（空）
        assert description_generator.validate_content("") is False
        
        # 無効な概要（セクションなし）
        invalid_description = "# タイトルのみ"
        assert description_generator.validate_content(invalid_description) is False

    def test_append_template(self, description_generator):
        """テンプレート追記のテスト"""
        # 基本概要文
        description = """# テスト概要

## セクション1

これはテストセクション1です。
"""
        
        # テンプレート内容
        template = """
## テンプレートセクション

これはテンプレートから追加されたセクションです。

- 項目1: {{value1}}
- 項目2: {{value2}}
"""
        
        # テンプレート変数
        context = {
            "value1": "テスト値1",
            "value2": "テスト値2"
        }
        
        # テンプレート追記実行
        result = description_generator.append_template(description, template, context)
        
        # 結果の検証
        assert "# テスト概要" in result
        assert "## セクション1" in result
        assert "## テンプレートセクション" in result
        assert "これはテンプレートから追加されたセクションです。" in result
        assert "- 項目1: テスト値1" in result
        assert "- 項目2: テスト値2" in result 