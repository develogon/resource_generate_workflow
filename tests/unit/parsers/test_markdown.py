"""Markdownパーサーのテスト."""

import tempfile
from pathlib import Path

import pytest

from src.parsers.markdown import (
    MarkdownParser,
    ParsedCodeBlock,
    ParsedHeading,
    ParsedImage,
    ParsedLink,
    ParsedTable,
)


class TestParsedHeading:
    """ParsedHeadingのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        heading = ParsedHeading(
            element_type="heading",
            content="テストヘッディング",
            level=2,
            line_number=5
        )
        
        assert heading.element_type == "heading"
        assert heading.content == "テストヘッディング"
        assert heading.level == 2
        assert heading.line_number == 5
        assert heading.anchor == "テストヘッディング"
    
    def test_anchor_generation(self):
        """アンカー生成のテスト."""
        heading = ParsedHeading(
            element_type="heading",
            content="Test Heading with Spaces & Special-Chars!",
            level=1
        )
        
        # 特殊文字が除去され、スペースがハイフンに変換される
        assert heading.anchor == "test-heading-with-spaces-special-chars"
    
    def test_custom_anchor(self):
        """カスタムアンカーのテスト."""
        heading = ParsedHeading(
            element_type="heading",
            content="Test",
            level=1,
            anchor="custom-anchor"
        )
        
        assert heading.anchor == "custom-anchor"


class TestParsedCodeBlock:
    """ParsedCodeBlockのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        code_block = ParsedCodeBlock(
            element_type="code_block",
            content="print('hello')",
            language="python",
            filename="test.py",
            line_number=10
        )
        
        assert code_block.element_type == "code_block"
        assert code_block.content == "print('hello')"
        assert code_block.language == "python"
        assert code_block.filename == "test.py"
        assert code_block.line_number == 10


class TestMarkdownParser:
    """MarkdownParserのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        parser = MarkdownParser()
        
        assert len(parser.elements) == 0
        assert len(parser.headings) == 0
        assert len(parser.code_blocks) == 0
        assert len(parser.images) == 0
        assert len(parser.links) == 0
        assert len(parser.tables) == 0
        assert parser.front_matter == {}
        assert parser.content_without_frontmatter == ""
    
    def test_reset(self):
        """リセットのテスト."""
        parser = MarkdownParser()
        
        # 何らかのデータを設定
        parser.headings.append(ParsedHeading(element_type="heading", content="test", level=1))
        parser.front_matter = {"title": "test"}
        
        parser.reset()
        
        assert len(parser.headings) == 0
        assert parser.front_matter == {}
    
    def test_parse_basic_content(self):
        """基本的なコンテンツのパース."""
        content = """# メインタイトル

これは段落です。

## サブタイトル

別の段落です。
"""
        
        parser = MarkdownParser()
        result = parser.parse(content)
        
        assert result["validation"]["valid"]
        assert len(result["headings"]) == 2
        assert result["headings"][0].content == "メインタイトル"
        assert result["headings"][0].level == 1
        assert result["headings"][1].content == "サブタイトル"
        assert result["headings"][1].level == 2
        
        # 構造の確認
        structure = result["structure"]
        assert len(structure["chapters"]) == 1
        assert structure["chapters"][0]["title"] == "メインタイトル"
        assert len(structure["chapters"][0]["sections"]) == 1
        assert structure["chapters"][0]["sections"][0]["title"] == "サブタイトル"
    
    def test_parse_front_matter(self):
        """front matterのパース."""
        content = """---
title: テスト記事
author: テスト太郎
date: 2024-01-01
---

# コンテンツ

本文です。
"""
        
        parser = MarkdownParser()
        result = parser.parse(content)
        
        assert result["front_matter"]["title"] == "テスト記事"
        assert result["front_matter"]["author"] == "テスト太郎"
        assert str(result["front_matter"]["date"]) == "2024-01-01"
        assert "# コンテンツ" in result["content"]
    
    def test_parse_code_blocks(self):
        """コードブロックのパース."""
        content = """# タイトル

```python
def hello():
    print("Hello, World!")
```

```javascript
console.log("Hello, World!");
```

```
プレーンテキスト
```
"""
        
        parser = MarkdownParser()
        result = parser.parse(content)
        
        assert len(result["code_blocks"]) == 3
        
        python_block = result["code_blocks"][0]
        assert python_block.language == "python"
        assert "def hello():" in python_block.content
        
        js_block = result["code_blocks"][1]
        assert js_block.language == "javascript"
        assert "console.log" in js_block.content
        
        plain_block = result["code_blocks"][2]
        assert plain_block.language == ""
        assert "プレーンテキスト" in plain_block.content
    
    def test_parse_images(self):
        """画像のパース."""
        content = """# タイトル

![代替テキスト](image.png)
![説明付き画像](diagram.jpg "図表1")
![](no-alt.gif)
"""
        
        parser = MarkdownParser()
        result = parser.parse(content)
        
        assert len(result["images"]) == 3
        
        img1 = result["images"][0]
        assert img1.alt_text == "代替テキスト"
        assert img1.url == "image.png"
        assert img1.title == ""
        
        img2 = result["images"][1]
        assert img2.alt_text == "説明付き画像"
        assert img2.url == "diagram.jpg"
        assert img2.title == "図表1"
        
        img3 = result["images"][2]
        assert img3.alt_text == ""
        assert img3.url == "no-alt.gif"
    
    def test_parse_links(self):
        """リンクのパース."""
        content = """# タイトル

[Google](https://google.com)
[ドキュメント](doc.html "説明")
[内部リンク](./internal.md)
"""
        
        parser = MarkdownParser()
        result = parser.parse(content)
        
        assert len(result["links"]) == 3
        
        link1 = result["links"][0]
        assert link1.text == "Google"
        assert link1.url == "https://google.com"
        assert link1.title == ""
        
        link2 = result["links"][1]
        assert link2.text == "ドキュメント"
        assert link2.url == "doc.html"
        assert link2.title == "説明"
    
    def test_parse_tables(self):
        """テーブルのパース."""
        content = """# タイトル

| 名前 | 年齢 | 職業 |
|------|------|------|
| 太郎 | 25   | エンジニア |
| 花子 | 30   | デザイナー |
"""
        
        parser = MarkdownParser()
        result = parser.parse(content)
        
        assert len(result["tables"]) == 1
        
        table = result["tables"][0]
        assert table.headers == ["名前", "年齢", "職業"]
        assert len(table.rows) == 2
        assert table.rows[0] == ["太郎", "25", "エンジニア"]
        assert table.rows[1] == ["花子", "30", "デザイナー"]
    
    def test_build_hierarchy(self):
        """階層構造の構築テスト."""
        content = """# 第1章

## 1.1 セクション

### 1.1.1 サブセクション

## 1.2 別のセクション

# 第2章

## 2.1 セクション
"""
        
        parser = MarkdownParser()
        result = parser.parse(content)
        
        hierarchy = result["structure"]["hierarchy"]
        assert len(hierarchy) == 2
        
        # 第1章の構造
        chapter1 = hierarchy[0]
        assert chapter1["title"] == "第1章"
        assert chapter1["level"] == 1
        assert len(chapter1["children"]) == 2
        
        section1_1 = chapter1["children"][0]
        assert section1_1["title"] == "1.1 セクション"
        assert section1_1["level"] == 2
        assert len(section1_1["children"]) == 1
        
        subsection = section1_1["children"][0]
        assert subsection["title"] == "1.1.1 サブセクション"
        assert subsection["level"] == 3
        assert len(subsection["children"]) == 0
    
    def test_parse_file(self):
        """ファイルからのパース."""
        content = """# テストファイル

これはテストファイルです。
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            parser = MarkdownParser()
            result = parser.parse_file(temp_path)
            
            assert result["validation"]["valid"]
            assert len(result["headings"]) == 1
            assert result["headings"][0].content == "テストファイル"
        finally:
            temp_path.unlink()
    
    def test_to_content_models(self):
        """Contentモデルへの変換テスト."""
        content = """# 第1章

## セクション1

段落内容です。
"""
        
        parser = MarkdownParser()
        parsed_data = parser.parse(content)
        content_models = parser.to_content_models(parsed_data)
        
        assert len(content_models) == 1
        
        chapter = content_models[0]
        assert chapter.title == "第1章"
        assert len(chapter.sections) == 1
        
        section = chapter.sections[0]
        assert section.title == "セクション1"
    
    def test_extract_metadata(self):
        """メタデータ抽出のテスト."""
        content = """---
title: テスト記事
author: テスト太郎
---

# タイトル

```python
print("hello")
```

![画像](test.png)
"""
        
        parser = MarkdownParser()
        parsed_data = parser.parse(content)
        metadata = parser.extract_metadata(parsed_data)
        
        assert metadata["title"] == "テスト記事"
        assert metadata["author"] == "テスト太郎"
        assert metadata["heading_count"] == 1
        assert metadata["code_block_count"] == 1
        assert metadata["image_count"] == 1
        assert metadata["chapter_count"] == 1
        assert metadata["max_heading_level"] == 1
    
    def test_invalid_markdown(self):
        """不正なMarkdownの処理."""
        content = """# タイトル

```python
# 未閉じのコードブロック

[不正なリンク](
"""
        
        parser = MarkdownParser()
        result = parser.parse(content)
        
        # バリデーションエラーが検出される
        assert not result["validation"]["valid"]
        assert len(result["validation"]["errors"]) > 0
    
    def test_complex_structure(self):
        """複雑な構造のテスト."""
        content = """---
title: 複雑な文書
---

# はじめに

導入部分です。

# 第1章: 基礎

## 1.1 概要

概要の説明です。

```python
def example():
    pass
```

![図1](figure1.png "サンプル図")

## 1.2 詳細

詳細の説明です。

| 項目 | 値 |
|------|-----|
| A    | 1   |
| B    | 2   |

# 第2章: 応用

## 2.1 実装

実装例です。

```javascript
console.log("example");
```

[参考資料](https://example.com)
"""
        
        parser = MarkdownParser()
        result = parser.parse(content)
        
        # 基本的な解析結果の確認
        assert result["validation"]["valid"]
        assert len(result["headings"]) == 6
        assert len(result["code_blocks"]) == 2
        assert len(result["images"]) == 1
        assert len(result["links"]) == 1
        assert len(result["tables"]) == 1
        
        # 構造の確認
        structure = result["structure"]
        assert len(structure["chapters"]) == 3  # はじめに、第1章、第2章
        
        # front matterの確認
        assert result["front_matter"]["title"] == "複雑な文書" 