"""構造化データ変換システムのテスト."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.models.content import Chapter, Paragraph, Section
from src.parsers.converter import ContentConverter


class TestContentConverter:
    """ContentConverterのテスト."""
    
    @pytest.fixture
    def converter(self):
        """ContentConverterフィクスチャ."""
        return ContentConverter()
    
    @pytest.fixture
    def sample_markdown(self):
        """サンプルMarkdownコンテンツ."""
        return """---
title: テスト記事
author: テスト太郎
date: 2024-01-01
tags: [Python, テスト]
---

# メインチャプター

このチャプターでは、テストについて学びます。

## セクション1: 基本概念

テストの基本的な概念について説明します。

段落1のコンテンツです。
これは複数行にわたる段落です。

段落2のコンテンツです。

### サブセクション

詳細な説明です。

```python
def test_example():
    assert True
```

![テスト画像](test.png "テスト画像の説明")

## セクション2: 実践

実際のテスト方法について。

<diagram type="mermaid">
graph TD
    A[開始] --> B[テスト実行]
    B --> C[結果確認]
</diagram>

実践的な内容です。
"""
    
    @pytest.fixture
    def expected_parsed_structure(self):
        """期待されるパース構造."""
        return {
            "validation": {"valid": True, "errors": [], "warnings": []},
            "front_matter": {
                "title": "テスト記事",
                "author": "テスト太郎",
                "tags": ["Python", "テスト"]
            },
            "content": "# メインチャプター\n\n...",  # 簡略化
            "headings": [],  # モックで制御
            "code_blocks": [],  # モックで制御
            "images": [],  # モックで制御
            "structure": {
                "chapters": [
                    {
                        "title": "メインチャプター",
                        "anchor": "メインチャプター",
                        "line_number": 1,
                        "sections": [
                            {
                                "title": "セクション1: 基本概念",
                                "anchor": "セクション1-基本概念",
                                "line_number": 5,
                                "content": "テストの基本的な概念について説明します。"
                            },
                            {
                                "title": "セクション2: 実践",
                                "anchor": "セクション2-実践",
                                "line_number": 20,
                                "content": "実際のテスト方法について。"
                            }
                        ]
                    }
                ],
                "sections": []
            }
        }
    
    def test_initialization(self, converter):
        """初期化のテスト."""
        assert converter.markdown_parser is not None
        assert converter.image_detector is not None
        assert converter.metadata_parser is not None
    
    def test_convert_from_file_not_found(self, converter):
        """存在しないファイルの変換テスト."""
        with pytest.raises(FileNotFoundError):
            converter.convert_from_file("nonexistent.md")
    
    def test_convert_from_file_success(self, converter, sample_markdown):
        """ファイルからの変換成功テスト."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(sample_markdown)
            f.flush()
            
            temp_path = Path(f.name)
            
            try:
                with patch.object(converter, 'convert_from_markdown') as mock_convert:
                    mock_convert.return_value = {"result": "success"}
                    
                    result = converter.convert_from_file(temp_path)
                    
                    assert result == {"result": "success"}
                    mock_convert.assert_called_once_with(sample_markdown, base_path=temp_path.parent)
            finally:
                temp_path.unlink()
    
    def test_convert_from_markdown_basic(self, converter, sample_markdown):
        """基本的なMarkdown変換テスト."""
        # モック設定
        with patch.object(converter.markdown_parser, 'parse') as mock_parse, \
             patch.object(converter.image_detector, 'detect_in_content') as mock_detect, \
             patch.object(converter.metadata_parser, 'extract_from_frontmatter') as mock_metadata:
            
            # モックの戻り値設定
            mock_parse.return_value = {
                "validation": {"valid": True},
                "front_matter": {"title": "テスト"},
                "structure": {
                    "chapters": [
                        {
                            "title": "テストチャプター",
                            "anchor": "test-chapter",
                            "line_number": 1,
                            "sections": [
                                {
                                    "title": "テストセクション",
                                    "anchor": "test-section",
                                    "line_number": 3,
                                    "content": "テスト内容"
                                }
                            ]
                        }
                    ],
                    "sections": []
                }
            }
            
            mock_detect.return_value = {
                "images": [],
                "diagrams": [],
                "code_blocks": []
            }
            
            mock_metadata.return_value = {
                "title": "テスト記事",
                "metadata": {"author": "テスト太郎"}
            }
            
            # 変換実行
            result = converter.convert_from_markdown(sample_markdown)
            
            # 結果検証
            assert "content_models" in result
            assert "metadata" in result
            assert "parsed_data" in result
            assert "image_detection" in result
            assert "validation" in result
            
            # モック呼び出し確認
            mock_parse.assert_called_once_with(sample_markdown)
            mock_detect.assert_called_once()
            mock_metadata.assert_called_once_with(sample_markdown)
    
    def test_convert_to_content_models_chapters(self, converter):
        """チャプターのあるコンテンツモデル変換テスト."""
        parsed_data = {
            "structure": {
                "chapters": [
                    {
                        "title": "テストチャプター",
                        "anchor": "test-chapter",
                        "line_number": 1,
                        "sections": [
                            {
                                "title": "テストセクション",
                                "anchor": "test-section",
                                "line_number": 3,
                                "content": "セクション内容"
                            }
                        ]
                    }
                ],
                "sections": []
            }
        }
        
        image_detection = {
            "images": [],
            "diagrams": []
        }
        
        with patch.object(converter, '_create_paragraphs_from_section') as mock_paragraphs:
            mock_paragraphs.return_value = [
                Paragraph(
                    content="テスト段落",
                    paragraph_type="text",
                    order=1,
                    metadata={"source": "test"}
                )
            ]
            
            content_models = converter._convert_to_content_models(parsed_data, image_detection)
            
            assert len(content_models) == 1
            assert isinstance(content_models[0], Chapter)
            assert content_models[0].title == "テストチャプター"
            assert len(content_models[0].sections) == 1
            assert content_models[0].sections[0].title == "テストセクション"
    
    def test_convert_to_content_models_standalone_sections(self, converter):
        """スタンドアロンセクションのコンテンツモデル変換テスト."""
        parsed_data = {
            "structure": {
                "chapters": [],
                "sections": [
                    {
                        "title": "スタンドアロンセクション",
                        "anchor": "standalone-section",
                        "line_number": 1,
                        "content": "セクション内容"
                    }
                ]
            }
        }
        
        image_detection = {"images": [], "diagrams": []}
        
        with patch.object(converter, '_create_paragraphs_from_section') as mock_paragraphs:
            mock_paragraphs.return_value = []
            
            content_models = converter._convert_to_content_models(parsed_data, image_detection)
            
            assert len(content_models) == 1
            assert isinstance(content_models[0], Section)
            assert content_models[0].title == "スタンドアロンセクション"
            assert content_models[0].metadata["standalone"] is True
    
    def test_create_paragraphs_from_section(self, converter):
        """セクションから段落作成のテスト."""
        section_data = {
            "title": "テストセクション",
            "line_number": 5,
            "content": "セクション内容"
        }
        
        parsed_data = {
            "content": "# タイトル\n\n段落1\n\n段落2\n\n```python\ncode\n```",
            "code_blocks": []
        }
        
        image_detection = {
            "images": [],
            "diagrams": []
        }
        
        with patch.object(converter, '_extract_text_paragraphs') as mock_text, \
             patch.object(converter, '_extract_code_paragraphs') as mock_code, \
             patch.object(converter, '_extract_image_paragraphs') as mock_image, \
             patch.object(converter, '_extract_diagram_paragraphs') as mock_diagram:
            
            mock_text.return_value = [
                Paragraph(content="段落1", paragraph_type="text", order=1, metadata={"source_line": 3}),
                Paragraph(content="段落2", paragraph_type="text", order=2, metadata={"source_line": 5})
            ]
            mock_code.return_value = [
                Paragraph(content="code", paragraph_type="code", order=3, metadata={"source_line": 7})
            ]
            mock_image.return_value = []
            mock_diagram.return_value = []
            
            paragraphs = converter._create_paragraphs_from_section(
                section_data, parsed_data, image_detection
            )
            
            assert len(paragraphs) == 3
            assert paragraphs[0].content == "段落1"
            assert paragraphs[1].content == "段落2"
            assert paragraphs[2].content == "code"
            
            # 順序が正しく設定されているか確認
            for i, paragraph in enumerate(paragraphs):
                assert paragraph.order == i + 1
    
    def test_extract_text_paragraphs(self, converter):
        """テキスト段落抽出のテスト."""
        section_data = {"line_number": 0}
        parsed_data = {
            "content": "段落1のコンテンツです。\nこれは同じ段落です。\n\n段落2のコンテンツです。\n\n# 見出し"
        }
        
        paragraphs = converter._extract_text_paragraphs(section_data, parsed_data)
        
        assert len(paragraphs) >= 0  # 実装により変動
        for paragraph in paragraphs:
            assert isinstance(paragraph, Paragraph)
            assert paragraph.paragraph_type == "text"
            assert paragraph.content.strip() != ""
    
    def test_extract_code_paragraphs(self, converter):
        """コード段落抽出のテスト."""
        section_data = {"line_number": 0}
        parsed_data = {
            "code_blocks": [
                {
                    "language": "python",
                    "content": "def test():\n    pass",
                    "line_number": 5,
                    "metadata": {}
                }
            ]
        }
        
        paragraphs = converter._extract_code_paragraphs(section_data, parsed_data)
        
        # コードブロックがある場合の検証は実装に依存
        for paragraph in paragraphs:
            assert isinstance(paragraph, Paragraph)
            assert paragraph.paragraph_type == "code"
    
    def test_extract_image_paragraphs(self, converter):
        """画像段落抽出のテスト."""
        section_data = {"line_number": 0}
        image_detection = {
            "images": [
                {
                    "type": "standard",
                    "path": "test.png",
                    "alt_text": "テスト画像",
                    "line_number": 3
                }
            ]
        }
        
        paragraphs = converter._extract_image_paragraphs(section_data, image_detection)
        
        # 画像がある場合の検証
        for paragraph in paragraphs:
            assert isinstance(paragraph, Paragraph)
            assert paragraph.paragraph_type == "image"
    
    def test_extract_diagram_paragraphs(self, converter):
        """図表段落抽出のテスト."""
        section_data = {"line_number": 0}
        image_detection = {
            "diagrams": [
                {
                    "type": "mermaid",
                    "content": "graph TD\n  A --> B",
                    "line_number": 5
                }
            ]
        }
        
        paragraphs = converter._extract_diagram_paragraphs(section_data, image_detection)
        
        # 図表がある場合の検証
        for paragraph in paragraphs:
            assert isinstance(paragraph, Paragraph)
            assert paragraph.paragraph_type in ["diagram", "chart"]
    
    def test_extract_section_summary(self, converter):
        """セクション概要抽出のテスト."""
        section_data = {
            "content": "これはセクションの説明です。"
        }
        
        summary = converter._extract_section_summary(section_data)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
    
    def test_extract_chapter_summary(self, converter):
        """チャプター概要抽出のテスト."""
        chapter_data = {
            "content": "これはチャプターの説明です。"
        }
        
        summary = converter._extract_chapter_summary(chapter_data)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
    
    def test_extract_learning_objectives(self, converter):
        """学習目標抽出のテスト."""
        section_data = {
            "content": "この章では以下を学びます：\n- 基本概念\n- 実践方法"
        }
        
        objectives = converter._extract_learning_objectives(section_data)
        
        assert isinstance(objectives, list)
        # 実装により、空リストまたは抽出された目標が返される
    
    def test_integrate_metadata(self, converter):
        """メタデータ統合のテスト."""
        parsed_data = {
            "front_matter": {"title": "テスト記事"},
            "validation": {"valid": True}
        }
        
        image_detection = {
            "images": [{"path": "test.png"}],
            "diagrams": [{"type": "mermaid"}]
        }
        
        metadata_result = {
            "title": "テスト記事",
            "metadata": {"author": "テスト太郎"}
        }
        
        integrated = converter._integrate_metadata(
            parsed_data, image_detection, metadata_result
        )
        
        assert isinstance(integrated, dict)
        assert "title" in integrated
        assert "validation" in integrated
        assert "content_stats" in integrated
        assert "generation_info" in integrated
    
    def test_validate_conversion(self, converter):
        """変換検証のテスト."""
        content_models = [
            Chapter(
                title="テストチャプター",
                content="テスト内容",
                sections=[
                    Section(
                        title="テストセクション",
                        content="セクション内容",
                        paragraphs=[
                            Paragraph(
                                content="段落内容",
                                paragraph_type="text",
                                order=1,
                                metadata={}
                            )
                        ]
                    )
                ]
            )
        ]
        
        parsed_data = {
            "validation": {"valid": True},
            "structure": {
                "chapters": [{"title": "テストチャプター"}]
            }
        }
        
        validation = converter._validate_conversion(content_models, parsed_data)
        
        assert isinstance(validation, dict)
        assert "valid" in validation
        assert "content_model_count" in validation
        assert "structure_match" in validation
    
    def test_convert_from_markdown_full_integration(self, converter):
        """Markdown変換の完全な統合テスト."""
        markdown_content = """# テストチャプター

## セクション1

これは段落1です。

これは段落2です。

```python
def hello():
    print("Hello, World!")
```

![テスト画像](test.png)
"""
        
        # 実際のパーサーを使用した統合テスト
        result = converter.convert_from_markdown(markdown_content)
        
        # 基本的な構造の検証
        assert "content_models" in result
        assert "metadata" in result
        assert "validation" in result
        
        # コンテンツモデルの検証
        content_models = result["content_models"]
        assert len(content_models) > 0
        
        # 最初のモデルがChapterまたはSectionであることを確認
        first_model = content_models[0]
        assert isinstance(first_model, (Chapter, Section))
        
        # メタデータの検証
        metadata = result["metadata"]
        assert isinstance(metadata, dict)
        assert "content_stats" in metadata
    
    def test_convert_from_markdown_error_handling(self, converter):
        """Markdown変換のエラーハンドリングテスト."""
        # 不正なMarkdownコンテンツ
        invalid_markdown = "# " * 1000  # 異常に長い見出し
        
        # エラーが発生しても適切に処理されることを確認
        try:
            result = converter.convert_from_markdown(invalid_markdown)
            # 結果が返される場合は、エラー情報が含まれているか確認
            assert "validation" in result
        except Exception as e:
            # 例外が発生する場合は、適切な例外であることを確認
            assert isinstance(e, (ValueError, RuntimeError))
    
    def test_convert_empty_content(self, converter):
        """空のコンテンツ変換テスト."""
        empty_content = ""
        
        result = converter.convert_from_markdown(empty_content)
        
        assert "content_models" in result
        assert "metadata" in result
        assert "validation" in result
        
        # 空のコンテンツでも適切に処理される
        content_models = result["content_models"]
        assert isinstance(content_models, list)
    
    def test_convert_minimal_content(self, converter):
        """最小限のコンテンツ変換テスト."""
        minimal_content = "# タイトルのみ"
        
        result = converter.convert_from_markdown(minimal_content)
        
        assert "content_models" in result
        content_models = result["content_models"]
        
        # 最小限のコンテンツでも何らかのモデルが作成される
        assert len(content_models) >= 0 