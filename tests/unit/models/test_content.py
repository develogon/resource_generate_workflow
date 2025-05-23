"""コンテンツモデルのテスト."""

import pytest

from src.models.content import Chapter, Content, Paragraph, Section


class TestContent:
    """Contentクラスのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        content = Content(
            id="test_id",
            title="テストタイトル",
            content="テストコンテンツ"
        )
        
        assert content.id == "test_id"
        assert content.title == "テストタイトル"
        assert content.content == "テストコンテンツ"
        assert content.metadata == {}
    
    def test_initialization_with_metadata(self):
        """メタデータ付き初期化のテスト."""
        metadata = {"author": "test_author", "version": "1.0"}
        content = Content(
            id="test_id",
            title="テストタイトル",
            content="テストコンテンツ",
            metadata=metadata
        )
        
        assert content.metadata == metadata
    
    def test_to_dict(self):
        """辞書変換のテスト."""
        metadata = {"key": "value"}
        content = Content(
            id="test_id",
            title="テストタイトル",
            content="テストコンテンツ",
            metadata=metadata
        )
        
        data = content.to_dict()
        
        expected = {
            "id": "test_id",
            "title": "テストタイトル",
            "content": "テストコンテンツ",
            "metadata": metadata
        }
        assert data == expected
    
    def test_from_dict(self):
        """辞書からの復元のテスト."""
        data = {
            "id": "test_id",
            "title": "テストタイトル",
            "content": "テストコンテンツ",
            "metadata": {"key": "value"}
        }
        
        content = Content.from_dict(data)
        
        assert content.id == "test_id"
        assert content.title == "テストタイトル"
        assert content.content == "テストコンテンツ"
        assert content.metadata == {"key": "value"}
    
    def test_from_dict_minimal(self):
        """最小限のデータからの復元テスト."""
        data = {
            "id": "test_id",
            "title": "テストタイトル",
            "content": "テストコンテンツ"
        }
        
        content = Content.from_dict(data)
        
        assert content.id == "test_id"
        assert content.title == "テストタイトル"
        assert content.content == "テストコンテンツ"
        assert content.metadata == {}


class TestParagraph:
    """Paragraphクラスのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        paragraph = Paragraph(
            id="para_1",
            title="パラグラフ1",
            content="パラグラフコンテンツ",
            type="introduction",
            order=1,
            content_focus="概要説明",
            original_text="元のテキスト"
        )
        
        assert paragraph.id == "para_1"
        assert paragraph.title == "パラグラフ1"
        assert paragraph.content == "パラグラフコンテンツ"
        assert paragraph.type == "introduction"
        assert paragraph.order == 1
        assert paragraph.content_focus == "概要説明"
        assert paragraph.original_text == "元のテキスト"
        assert paragraph.content_sequence == []
    
    def test_to_dict(self):
        """辞書変換のテスト."""
        content_sequence = [{"type": "text", "content": "テキスト"}]
        paragraph = Paragraph(
            id="para_1",
            title="パラグラフ1",
            content="パラグラフコンテンツ",
            type="introduction",
            order=1,
            content_focus="概要説明",
            original_text="元のテキスト",
            content_sequence=content_sequence
        )
        
        data = paragraph.to_dict()
        
        assert data["id"] == "para_1"
        assert data["title"] == "パラグラフ1"
        assert data["content"] == "パラグラフコンテンツ"
        assert data["type"] == "introduction"
        assert data["order"] == 1
        assert data["content_focus"] == "概要説明"
        assert data["original_text"] == "元のテキスト"
        assert data["content_sequence"] == content_sequence
    
    def test_from_dict(self):
        """辞書からの復元のテスト."""
        data = {
            "id": "para_1",
            "title": "パラグラフ1",
            "content": "パラグラフコンテンツ",
            "type": "introduction",
            "order": 1,
            "content_focus": "概要説明",
            "original_text": "元のテキスト",
            "content_sequence": [{"type": "text"}]
        }
        
        paragraph = Paragraph.from_dict(data)
        
        assert paragraph.id == "para_1"
        assert paragraph.type == "introduction"
        assert paragraph.order == 1
        assert paragraph.content_focus == "概要説明"
        assert paragraph.original_text == "元のテキスト"
        assert paragraph.content_sequence == [{"type": "text"}]


class TestSection:
    """Sectionクラスのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        learning_objectives = ["目標1", "目標2"]
        section = Section(
            id="section_1",
            title="セクション1",
            content="セクションコンテンツ",
            index=1,
            learning_objectives=learning_objectives
        )
        
        assert section.id == "section_1"
        assert section.title == "セクション1"
        assert section.content == "セクションコンテンツ"
        assert section.index == 1
        assert section.learning_objectives == learning_objectives
        assert section.paragraphs == []
    
    def test_add_paragraph(self):
        """パラグラフ追加のテスト."""
        section = Section(
            id="section_1",
            title="セクション1",
            content="セクションコンテンツ"
        )
        
        paragraph = Paragraph(
            id="para_1",
            title="パラグラフ1",
            content="パラグラフコンテンツ"
        )
        
        section.add_paragraph(paragraph)
        
        assert len(section.paragraphs) == 1
        assert section.paragraphs[0] == paragraph
    
    def test_to_dict(self):
        """辞書変換のテスト."""
        paragraph = Paragraph(
            id="para_1",
            title="パラグラフ1",
            content="パラグラフコンテンツ"
        )
        
        section = Section(
            id="section_1",
            title="セクション1",
            content="セクションコンテンツ",
            index=1,
            learning_objectives=["目標1"],
            paragraphs=[paragraph]
        )
        
        data = section.to_dict()
        
        assert data["id"] == "section_1"
        assert data["index"] == 1
        assert data["learning_objectives"] == ["目標1"]
        assert len(data["paragraphs"]) == 1
        assert data["paragraphs"][0]["id"] == "para_1"
    
    def test_from_dict(self):
        """辞書からの復元のテスト."""
        data = {
            "id": "section_1",
            "title": "セクション1",
            "content": "セクションコンテンツ",
            "index": 1,
            "learning_objectives": ["目標1"],
            "paragraphs": [
                {
                    "id": "para_1",
                    "title": "パラグラフ1",
                    "content": "パラグラフコンテンツ"
                }
            ]
        }
        
        section = Section.from_dict(data)
        
        assert section.id == "section_1"
        assert section.index == 1
        assert section.learning_objectives == ["目標1"]
        assert len(section.paragraphs) == 1
        assert section.paragraphs[0].id == "para_1"


class TestChapter:
    """Chapterクラスのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        chapter = Chapter(
            id="chapter_1",
            title="チャプター1",
            content="チャプターコンテンツ",
            index=1
        )
        
        assert chapter.id == "chapter_1"
        assert chapter.title == "チャプター1"
        assert chapter.content == "チャプターコンテンツ"
        assert chapter.index == 1
        assert chapter.sections == []
    
    def test_add_section(self):
        """セクション追加のテスト."""
        chapter = Chapter(
            id="chapter_1",
            title="チャプター1",
            content="チャプターコンテンツ"
        )
        
        section = Section(
            id="section_1",
            title="セクション1",
            content="セクションコンテンツ"
        )
        
        chapter.add_section(section)
        
        assert len(chapter.sections) == 1
        assert chapter.sections[0] == section
    
    def test_to_dict(self):
        """辞書変換のテスト."""
        section = Section(
            id="section_1",
            title="セクション1",
            content="セクションコンテンツ"
        )
        
        chapter = Chapter(
            id="chapter_1",
            title="チャプター1",
            content="チャプターコンテンツ",
            index=1,
            sections=[section]
        )
        
        data = chapter.to_dict()
        
        assert data["id"] == "chapter_1"
        assert data["index"] == 1
        assert len(data["sections"]) == 1
        assert data["sections"][0]["id"] == "section_1"
    
    def test_from_dict(self):
        """辞書からの復元のテスト."""
        data = {
            "id": "chapter_1",
            "title": "チャプター1",
            "content": "チャプターコンテンツ",
            "index": 1,
            "sections": [
                {
                    "id": "section_1",
                    "title": "セクション1",
                    "content": "セクションコンテンツ",
                    "paragraphs": []
                }
            ]
        }
        
        chapter = Chapter.from_dict(data)
        
        assert chapter.id == "chapter_1"
        assert chapter.index == 1
        assert len(chapter.sections) == 1
        assert chapter.sections[0].id == "section_1" 