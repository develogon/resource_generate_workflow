"""コンテンツ関連のデータモデル."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Content:
    """基本コンテンツクラス."""
    
    id: str
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Content:
        """辞書からインスタンスを作成."""
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class Paragraph(Content):
    """パラグラフクラス."""
    
    type: str = ""
    order: int = 0
    content_focus: str = ""
    original_text: str = ""
    content_sequence: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換."""
        data = super().to_dict()
        data.update({
            "type": self.type,
            "order": self.order,
            "content_focus": self.content_focus,
            "original_text": self.original_text,
            "content_sequence": self.content_sequence,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Paragraph:
        """辞書からインスタンスを作成."""
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            type=data.get("type", ""),
            order=data.get("order", 0),
            content_focus=data.get("content_focus", ""),
            original_text=data.get("original_text", ""),
            content_sequence=data.get("content_sequence", []),
        )


@dataclass 
class Section(Content):
    """セクションクラス."""
    
    index: int = 0
    learning_objectives: List[str] = field(default_factory=list)
    paragraphs: List[Paragraph] = field(default_factory=list)
    
    def add_paragraph(self, paragraph: Paragraph) -> None:
        """パラグラフを追加."""
        self.paragraphs.append(paragraph)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換."""
        data = super().to_dict()
        data.update({
            "index": self.index,
            "learning_objectives": self.learning_objectives,
            "paragraphs": [p.to_dict() for p in self.paragraphs],
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Section:
        """辞書からインスタンスを作成."""
        paragraphs = [
            Paragraph.from_dict(p) for p in data.get("paragraphs", [])
        ]
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            index=data.get("index", 0),
            learning_objectives=data.get("learning_objectives", []),
            paragraphs=paragraphs,
        )


@dataclass
class Chapter(Content):
    """チャプタークラス."""
    
    index: int = 0
    sections: List[Section] = field(default_factory=list)
    
    def add_section(self, section: Section) -> None:
        """セクションを追加."""
        self.sections.append(section)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換."""
        data = super().to_dict()
        data.update({
            "index": self.index,
            "sections": [s.to_dict() for s in self.sections],
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Chapter:
        """辞書からインスタンスを作成."""
        sections = [
            Section.from_dict(s) for s in data.get("sections", [])
        ]
        return cls(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            index=data.get("index", 0),
            sections=sections,
        ) 