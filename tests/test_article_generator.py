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
                    
                    # 分割と結合が呼ばれたことを確認
                    mock_split.assert_called_once()
                    mock_combine.assert_called_once()
                    
                    # ClaudeのAPIが2回呼ばれたことを確認
                    assert mock_claude_service.generate_content.call_count == 2
                    
                    # 結果の検証
                    assert result == "# 結合された記事\n\nチャンク1とチャンク2の結合内容\n"

    def test_split_content(self, article_generator):
        """コンテンツ分割のテスト"""
        # テスト用の長いコンテンツ
        paragraphs = []
        for i in range(20):
            paragraphs.append(f"パラグラフ{i+1}の内容です。これは分割テスト用のテキストです。" * 10)
        
        content = "\n\n".join(paragraphs)
        
        # 分割実行
        chunks = article_generator._split_content(content, max_chunk_size=1000)
        
        # 複数のチャンクに分割されたことを確認
        assert len(chunks) > 1
        
        # 各チャンクのサイズが最大サイズ以下であることを確認
        for chunk in chunks:
            assert len(chunk) <= 1000

    def test_combine_chunks(self, article_generator):
        """チャンク結合のテスト"""
        # テスト用のチャンク応答
        chunk_responses = [
            "# チャンク1\n\n## セクション1\n\nチャンク1の内容です。\n\n",
            "# チャンク2\n\n## セクション2\n\nチャンク2の内容です。\n\n",
            "# チャンク3\n\n## セクション3\n\nチャンク3の内容です。\n\n"
        ]
        
        # 結合実行
        combined = article_generator._combine_chunks(chunk_responses)
        
        # 結合結果の検証
        assert "# チャンク1" in combined  # 最初のタイトルは保持
        assert "## セクション1" in combined
        assert "チャンク1の内容です。" in combined
        
        assert "# チャンク2" not in combined  # 2つ目以降のタイトルは削除
        assert "## セクション2" in combined
        assert "チャンク2の内容です。" in combined
        
        assert "# チャンク3" not in combined  # 3つ目のタイトルも削除
        assert "## セクション3" in combined
        assert "チャンク3の内容です。" in combined 