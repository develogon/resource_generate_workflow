import pytest
import os
from unittest.mock import patch, MagicMock, mock_open

from core.processor import ContentProcessor
from core.parser import MarkdownParser
from generators.article import ArticleGenerator
from generators.script import ScriptGenerator
from generators.image.processor import ImageProcessor


class TestEndToEndWorkflow:
    """エンドツーエンドのワークフローテスト"""

    @pytest.fixture
    def mock_services(self):
        """モックサービス群"""
        mock_claude_service = MagicMock()
        mock_github_service = MagicMock()
        mock_storage_service = MagicMock()
        mock_notifier_service = MagicMock()
        mock_file_manager = MagicMock()
        mock_state_manager = MagicMock()
        
        return {
            "claude_service": mock_claude_service,
            "github_service": mock_github_service,
            "storage_service": mock_storage_service,
            "notifier_service": mock_notifier_service,
            "file_manager": mock_file_manager,
            "state_manager": mock_state_manager
        }

    @pytest.fixture
    def test_content(self):
        """テスト用Markdown原稿"""
        return """# Goプログラミング入門

## 第1章 Goの基礎

### 1.1 Goとは

Goは効率的で信頼性の高い静的型付け言語です。

```mermaid
graph TD
    A[Goの特徴] --> B[静的型付け]
    A --> C[ガベージコレクション]
    A --> D[並行処理]
```

### 1.2 開発環境のセットアップ

以下の手順で環境をセットアップします。

## 第2章 基本構文

### 2.1 変数と定数

変数は`var`キーワードで宣言します。

```go
package main

import "fmt"

func main() {
    var message string = "Hello, World!"
    fmt.Println(message)
}
```

### 2.2 制御構造

条件分岐とループについて説明します。
"""

    def test_full_workflow(self, mock_services, test_content, temp_dir):
        """完全なワークフローの統合テスト"""
        # テスト用のディレクトリとファイル
        base_dir = str(temp_dir)
        os.makedirs(os.path.join(base_dir, "til/go/test_title"), exist_ok=True)
        text_md_path = os.path.join(base_dir, "til/go/test_title/text.md")
        
        # Markdownファイル作成
        with open(text_md_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # モックサービスの設定
        mock_services["file_manager"].read_content.return_value = test_content
        mock_services["claude_service"].generate_content.return_value = {
            "content": "# Generated Article\n\nThis is a generated article."
        }
        
        # ディレクトリ構造作成のモック
        def create_directory_structure_mock(base_path, structure):
            created_paths = []
            for name, sub_structure in structure.items():
                path = os.path.join(base_path, name)
                created_paths.append(path)
                if sub_structure:
                    created_paths.extend(create_directory_structure_mock(path, sub_structure))
            return created_paths
        
        mock_services["file_manager"].create_directory_structure.side_effect = create_directory_structure_mock
        
        # テスト用引数
        args = MagicMock()
        args.title = "test_title"
        args.lang = "go"
        args.input_path = text_md_path
        args.output_dir = base_dir
        args.resume = None
        
        # プロセッサの初期化
        processor = ContentProcessor(
            content=test_content,
            args=args,
            file_manager=mock_services["file_manager"],
            claude_service=mock_services["claude_service"],
            github_service=mock_services["github_service"],
            storage_service=mock_services["storage_service"],
            state_manager=mock_services["state_manager"],
            notifier=mock_services["notifier_service"]
        )
        
        # 実際のメソッドをモックで置き換え
        with patch.object(processor, 'process_chapter') as mock_process_chapter:
            with patch.object(processor, 'process_section') as mock_process_section:
                with patch.object(processor, 'generate_article') as mock_generate_article:
                    with patch.object(processor, 'generate_script') as mock_generate_script:
                        with patch.object(processor, 'process_images') as mock_process_images:
                            # ワークフロー実行
                            processor.process()
                            
                            # 主要メソッドが呼ばれたことを確認
                            mock_process_chapter.assert_called()
                            mock_process_section.assert_called()
                            mock_generate_article.assert_called()
                            mock_generate_script.assert_called()
                            mock_process_images.assert_called()


class TestChapterSectionProcessing:
    """章・セクション処理のテスト"""
    
    @pytest.fixture
    def mock_services(self):
        """モックサービス群"""
        mock_claude_service = MagicMock()
        mock_github_service = MagicMock()
        mock_file_manager = MagicMock()
        
        return {
            "claude_service": mock_claude_service,
            "github_service": mock_github_service,
            "file_manager": mock_file_manager
        }
    
    @pytest.fixture
    def markdown_parser(self):
        """Markdownパーサー"""
        return MarkdownParser()
    
    def test_chapter_section_split(self, mock_services, markdown_parser, sample_markdown_content):
        """章・セクション分割の統合テスト"""
        # パーサーで章・セクションを抽出
        result = markdown_parser.parse_markdown(sample_markdown_content)
        
        # 結果の検証
        assert "title" in result
        assert "chapters" in result
        assert len(result["chapters"]) == 2
        
        # 章の内容が正しいことを確認
        chapter1 = result["chapters"][0]
        assert chapter1["title"] == "第1章 はじめに"
        assert len(chapter1["sections"]) == 2
        
        # セクションの内容が正しいことを確認
        section1 = chapter1["sections"][0]
        assert section1["title"] == "1.1 基礎知識"
        assert "このテキストは基礎知識についての説明です。" in section1["content"]
        
        # 画像の存在を確認
        sections = markdown_parser.extract_sections(sample_markdown_content)
        section_with_image = [s for s in sections if "mermaid" in s.get("content", "")]
        assert len(section_with_image) > 0


class TestArticleGeneration:
    """記事生成プロセスの統合テスト"""
    
    @pytest.fixture
    def mock_services(self):
        """モックサービス群"""
        mock_claude_service = MagicMock()
        mock_file_manager = MagicMock()
        return {
            "claude_service": mock_claude_service,
            "file_manager": mock_file_manager
        }
    
    def test_article_generation_with_images(self, mock_services):
        """画像を含む記事生成の統合テスト"""
        # モックレスポンス設定
        mock_services["claude_service"].generate_content.return_value = {
            "content": """# Goの基礎知識

## はじめに

Goの基本的な特徴について解説します。

## 主要な特徴

- 静的型付け
- ガベージコレクション
- 並行処理のサポート

## コード例

```go
package main

import "fmt"

func main() {
    fmt.Println("Hello, Go!")
}
```

## Goの概要図

![Goの概要](go_overview.png)
"""
        }
        
        # テンプレート読み込みのモック
        mock_open_obj = mock_open(read_data="""
        # テンプレート
        
        セクションタイトル: {{section_title}}
        言語: {{language}}
        """)
        
        # 記事生成器の初期化
        article_generator = ArticleGenerator(
            claude_service=mock_services["claude_service"],
            file_manager=mock_services["file_manager"]
        )
        
        # テスト用入力データ
        input_data = {
            "section_title": "Goの基礎知識",
            "content": "Goの基本的な特徴についての解説です。",
            "template_path": "templates/article.md",
            "images": ["data:image/png;base64,test_image_data"],
            "language": "Go"
        }
        
        # 記事生成テスト
        with patch('builtins.open', mock_open_obj):
            result = article_generator.generate(input_data)
            
            # 結果の検証
            assert "# Goの基礎知識" in result
            assert "## はじめに" in result
            assert "Goの基本的な特徴について解説します" in result
            assert "```go" in result
            assert "func main()" in result
            assert "![Goの概要](go_overview.png)" in result
            
            # API呼び出しの検証
            mock_services["claude_service"].generate_content.assert_called_once()
            
            # 画像が含まれていることを確認
            call_args = mock_services["claude_service"].generate_content.call_args[0]
            assert len(call_args) >= 2  # 引数が2つ以上（プロンプトと画像）


class TestImageProcessing:
    """画像処理の統合テスト"""
    
    @pytest.fixture
    def image_processor(self):
        """画像プロセッサ"""
        return ImageProcessor()
    
    @pytest.fixture
    def mock_storage_service(self):
        """モックストレージサービス"""
        mock = MagicMock()
        mock.upload_file.return_value = "https://example.com/image.png"
        return mock
    
    def test_mermaid_svg_processing(self, image_processor, mock_storage_service, temp_dir):
        """Mermaidとシンプル画像統合処理テスト"""
        # テスト用のMarkdown
        markdown_with_images = """# テスト

## Mermaid図

```mermaid
graph TD
    A[開始] --> B[処理]
    B --> C[終了]
```

## SVG図

<svg width="100" height="100">
  <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
</svg>
"""
        
        # 画像処理のモック
        with patch.object(image_processor, 'process_image') as mock_process:
            mock_process.return_value = os.path.join(str(temp_dir), "output.png")
            
            # Mermaid部分抽出
            mermaid_content = """graph TD
    A[開始] --> B[処理]
    B --> C[終了]"""
            
            # SVG部分抽出
            svg_content = """<svg width="100" height="100">
  <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
</svg>"""
            
            # Mermaid処理
            mermaid_output = image_processor.process_image(
                mermaid_content, 
                os.path.join(str(temp_dir), "mermaid.png")
            )
            
            # SVG処理
            svg_output = image_processor.process_image(
                svg_content,
                os.path.join(str(temp_dir), "svg.png")
            )
            
            # S3アップロード
            mermaid_url = mock_storage_service.upload_file(mermaid_output)
            svg_url = mock_storage_service.upload_file(svg_output)
            
            # 処理が行われたことを確認
            assert mock_process.call_count == 2
            
            # URLが生成されたことを確認
            assert mermaid_url == "https://example.com/image.png"
            assert svg_url == "https://example.com/image.png"
            
            # Markdown内の画像参照置換（置換関数のモック）
            replace_func = MagicMock()
            replace_func.return_value = markdown_with_images.replace(
                "```mermaid", 
                f"![Mermaid図]({mermaid_url})"
            ).replace(
                "<svg", 
                f"![SVG図]({svg_url})"
            )
            
            # 置換結果の検証
            result = replace_func(markdown_with_images)
            assert "![Mermaid図](https://example.com/image.png)" in result
            assert "![SVG図](https://example.com/image.png)" in result 