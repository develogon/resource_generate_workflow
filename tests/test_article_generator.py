import pytest
from unittest.mock import patch, MagicMock

from generators.article import ArticleGenerator


class TestArticleGenerator:
    """記事生成器のテストクラス"""

    @pytest.fixture
    def mock_claude_service(self):
        """モックClaudeサービス"""
        mock = MagicMock()
        mock.generate_content.return_value = {
            "content": """# テスト記事

## はじめに

これはテスト記事の内容です。

## コード例

```go
func main() {
    fmt.Println("Hello, World!")
}
```

## 画像例

![テスト画像](example.png)
"""
        }
        return mock

    @pytest.fixture
    def article_generator(self, mock_claude_service):
        """記事生成器のインスタンス"""
        file_manager = MagicMock()
        return ArticleGenerator(claude_service=mock_claude_service, file_manager=file_manager)

    def test_generate(self, article_generator, mock_claude_service):
        """記事生成のテスト"""
        input_data = {
            "section_title": "テストセクション",
            "content": "テスト原稿の内容",
            "template_path": "templates/article.md",
            "images": ["data:image/png;base64,test_image_data"],
            "language": "Go"
        }
        
        # テンプレート読み込みのモック
        with patch('builtins.open', MagicMock()) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
            # テンプレート
            
            セクションタイトル: {{section_title}}
            言語: {{language}}
            """
            
            # 記事生成実行
            result = article_generator.generate(input_data)
            
            # Claude APIが呼ばれたことを確認
            mock_claude_service.generate_content.assert_called_once()
            
            # 生成されたコンテンツの検証
            assert "# テスト記事" in result
            assert "## はじめに" in result
            assert "func main() {" in result
            assert "![テスト画像](example.png)" in result

    def test_generate_with_system_prompt(self, article_generator, mock_claude_service):
        """システムプロンプト付き記事生成のテスト"""
        input_data = {
            "section_title": "テストセクション",
            "content": "テスト原稿の内容",
            "template_path": "templates/article.md",
            "language": "Go",
            "system_prompt": "あなたはGo言語専門のドキュメント作成AIです。"
        }
        
        # テンプレート読み込みのモック
        article_generator.file_manager.read_content.return_value = """
        # テンプレート
        
        セクションタイトル: {{section_title}}
        言語: {{language}}
        """
        
        # 記事生成実行
        result = article_generator.generate(input_data)
        
        # Claude APIが正しいパラメータで呼ばれたことを確認
        mock_claude_service.generate_content.assert_called_once()
        call_args = mock_claude_service.generate_content.call_args
        
        # 引数の検証
        assert call_args[0][0] is not None  # プロンプト
        assert call_args[0][1] == []  # 画像（デフォルト空リスト）
        assert call_args[0][2] == "あなたはGo言語専門のドキュメント作成AIです。"  # システムプロンプト
        
        # 生成されたコンテンツの検証
        assert "# テスト記事" in result

    def test_format_output(self, article_generator):
        """出力フォーマットのテスト"""
        raw_content = """
        # 生成タイトル
        
        これは生成されたコンテンツです。
        
        ## セクション1
        
        - 項目1
        - 項目2
        
        ## セクション2
        
        コードサンプル:
        ```go
        package main
        
        import "fmt"
        
        func main() {
            fmt.Println("Hello")
        }
        ```
        """
        
        # フォーマット実行
        formatted = article_generator.format_output(raw_content)
        
        # 基本的なMarkdown構造が保持されていることを確認
        assert "# 生成タイトル" in formatted
        assert "## セクション1" in formatted
        assert "- 項目1" in formatted
        
        # コードブロックが保持されていることを確認
        assert "```go" in formatted
        assert "package main" in formatted
        assert "func main() {" in formatted

    def test_validate_content(self, article_generator):
        """コンテンツ検証のテスト"""
        # 有効な内容
        valid_content = """
        # 有効なタイトル
        
        これは有効な内容です。
        
        ## セクション
        
        テキスト。
        """
        assert article_generator.validate_content(valid_content) is True
        
        # 無効な内容（タイトルなし）
        invalid_content = """
        これはタイトルがない無効な内容です。
        """
        assert article_generator.validate_content(invalid_content) is False
        
        # 無効な内容（空）
        assert article_generator.validate_content("") is False

    def test_optimize_prompt(self, article_generator):
        """プロンプト最適化のテスト"""
        template = """
        # テンプレート
        
        セクションタイトル: {{section_title}}
        原稿内容: {{content}}
        言語: {{language}}
        画像: {{has_images}}
        """
        
        context = {
            "section_title": "テストセクション",
            "content": "短い原稿",
            "language": "Go",
            "has_images": True
        }
        
        # プロンプト最適化実行
        optimized = article_generator.optimize_prompt(template, context)
        
        # テンプレート変数が置換されていることを確認
        assert "セクションタイトル: テストセクション" in optimized
        assert "原稿内容: 短い原稿" in optimized
        assert "言語: Go" in optimized
        assert "画像: True" in optimized

    def test_generate_with_long_content(self, article_generator, mock_claude_service):
        """長い原稿の分割処理テスト"""
        # 長い原稿データの作成
        long_content = "テスト文章。" * 10000  # 十分に長いコンテンツ
        
        input_data = {
            "section_title": "長いセクション",
            "content": long_content,
            "template_path": "templates/article.md",
            "language": "Go"
        }
        
        # テンプレート読み込みのモック
        with patch('builtins.open', MagicMock()) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
            # テンプレート
            
            セクションタイトル: {{section_title}}
            言語: {{language}}
            """
            
            # 分割処理のモック
            with patch.object(article_generator, '_split_content') as mock_split:
                mock_split.return_value = [
                    "テスト文章。" * 500,  # チャンク1
                    "テスト文章。" * 500   # チャンク2
                ]
                
                # 複数回のAPI呼び出し結果をモック
                mock_claude_service.generate_content.side_effect = [
                    {"content": "# チャンク1の応答\n\nチャンク1の内容\n"},
                    {"content": "# チャンク2の応答\n\nチャンク2の内容\n"}
                ]
                
                # 結合処理のモック
                with patch.object(article_generator, '_combine_chunks') as mock_combine:
                    mock_combine.return_value = "# 結合された記事\n\nチャンク1とチャンク2の結合内容\n"
                    
                    # 記事生成実行
                    result = article_generator.generate(input_data)
                    
                    # 結果の検証
                    assert result == "# 結合された記事\n\nチャンク1とチャンク2の結合内容\n"
                    
                    # _split_contentが呼ばれたことを確認
                    mock_split.assert_called_once_with(long_content)
                    
                    # generateメソッドが2回呼ばれたことを確認
                    assert mock_claude_service.generate_content.call_count == 2
                    
                    # _combine_chunksが呼ばれたことを確認
                    mock_combine.assert_called_once()

    def test_generate_with_long_content_and_system_prompt(self, article_generator, mock_claude_service):
        """長い原稿とシステムプロンプトの組み合わせテスト"""
        # 長い原稿データの作成
        long_content = "テスト文章。" * 10000  # 十分に長いコンテンツ
        
        input_data = {
            "section_title": "長いセクション",
            "content": long_content,
            "template_path": "templates/article.md",
            "language": "Go",
            "system_prompt": "あなたはGo言語専門のドキュメント作成AIです。"
        }
        
        # テンプレート読み込みのモック
        article_generator.file_manager.read_content.return_value = """
        # テンプレート
        
        セクションタイトル: {{section_title}}
        言語: {{language}}
        """
        
        # 分割処理のモック
        with patch.object(article_generator, '_split_content') as mock_split:
            mock_split.return_value = [
                "テスト文章。" * 500,  # チャンク1
                "テスト文章。" * 500   # チャンク2
            ]
            
            # 複数回のAPI呼び出し結果をモック
            mock_claude_service.generate_content.side_effect = [
                {"content": "# チャンク1の応答\n\nチャンク1の内容\n"},
                {"content": "# チャンク2の応答\n\nチャンク2の内容\n"}
            ]
            
            # 結合処理のモック
            with patch.object(article_generator, '_combine_chunks') as mock_combine:
                mock_combine.return_value = "# 結合された記事\n\nチャンク1とチャンク2の結合内容\n"
                
                # 記事生成実行
                result = article_generator.generate(input_data)
                
                # 結果の検証
                assert result == "# 結合された記事\n\nチャンク1とチャンク2の結合内容\n"
                
                # システムプロンプトが各チャンクの処理に伝播されていることを確認
                for call_args in mock_claude_service.generate_content.call_args_list:
                    args = call_args[0]
                    # システムプロンプトが正しく渡されているか確認
                    assert args[2] == "あなたはGo言語専門のドキュメント作成AIです。"
                
                # _combine_chunksが呼ばれたことを確認
                mock_combine.assert_called_once()

    def test_split_content(self, article_generator):
        """コンテンツ分割のテスト"""
        # 段落で分割されるコンテンツ
        content = """これは最初の段落です。
        
        これは2番目の段落です。
        
        これは3番目の段落です。"""
        
        chunks = article_generator._split_content(content, max_chunk_size=50)
        
        # 適切な数のチャンクに分割されていることを確認
        assert len(chunks) > 0
        
        # 非常に長い文が文単位で分割されることを確認
        long_sentence_content = "これは非常に長い一つの文です。" * 100
        chunks = article_generator._split_content(long_sentence_content, max_chunk_size=50)
        
        # 長い文が適切に分割されていることを確認
        assert len(chunks) > 0

    def test_combine_chunks(self, article_generator):
        """チャンク結合のテスト"""
        # 複数のチャンク応答
        chunks = [
            """# テストタイトル
            
            ## 最初のセクション
            
            これは最初のチャンクの内容です。""",
            
            """# テストタイトル（続き）
            
            ## 2番目のセクション
            
            これは2番目のチャンクの内容です。""",
            
            """# テストタイトル（さらに続き）
            
            ## 3番目のセクション
            
            これは3番目のチャンクの内容です。"""
        ]
        
        combined = article_generator._combine_chunks(chunks)
        
        # タイトルが1つだけ残っていることを確認
        assert combined.count("# テストタイトル") == 1
        
        # 各セクションが含まれていることを確認
        assert "## 最初のセクション" in combined
        assert "## 2番目のセクション" in combined
        assert "## 3番目のセクション" in combined
        
        # 内容が順番通りに含まれていることを確認
        assert combined.index("最初のチャンク") < combined.index("2番目のチャンク")
        assert combined.index("2番目のチャンク") < combined.index("3番目のチャンク") 