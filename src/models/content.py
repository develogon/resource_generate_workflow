"""コンテンツモデル."""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path


@dataclass
class Content:
    """コンテンツデータモデル."""
    
    title: str
    content: str
    content_type: str = "text"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """初期化後処理."""
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def word_count(self) -> int:
        """単語数を取得."""
        return len(self.content.split())
    
    @property
    def char_count(self) -> int:
        """文字数を取得."""
        return len(self.content)
    
    def is_empty(self) -> bool:
        """コンテンツが空かどうか."""
        return not self.content or not self.content.strip()


@dataclass
class Chapter:
    """章モデル."""
    
    index: int
    title: str
    content: str
    sections: List['Section'] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """初期化後処理."""
        if self.sections is None:
            self.sections = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Section:
    """セクションモデル."""
    
    index: int
    title: str
    content: str
    chapter_index: int
    paragraphs: List['Paragraph'] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """初期化後処理."""
        if self.paragraphs is None:
            self.paragraphs = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Paragraph:
    """パラグラフモデル."""
    
    index: int
    content: str
    section_index: int
    chapter_index: int
    content_type: str = "text"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """初期化後処理."""
        if self.metadata is None:
            self.metadata = {} 