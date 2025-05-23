"""構造化データ変換システム."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..models.content import Chapter, Content, Paragraph, Section
from .image import ImageDetector
from .markdown import MarkdownParser
from .yaml import MetadataParser


class ContentConverter:
    """コンテンツ変換システム."""
    
    def __init__(self):
        """初期化."""
        self.markdown_parser = MarkdownParser()
        self.image_detector = ImageDetector()
        self.metadata_parser = MetadataParser()
    
    def convert_from_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """ファイルからコンテンツを変換."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.convert_from_markdown(content, base_path=path.parent)
    
    def convert_from_markdown(self, content: str, base_path: Optional[Path] = None) -> Dict[str, Any]:
        """Markdownコンテンツから構造化データに変換."""
        # Markdownのパース
        parsed_data = self.markdown_parser.parse(content)
        
        # 画像・図表の検出
        image_detection = self.image_detector.detect_in_content(
            content, 
            base_path or Path('.')
        )
        
        # メタデータの抽出
        metadata_result = self.metadata_parser.extract_from_frontmatter(content)
        
        # Contentモデルへの変換
        content_models = self._convert_to_content_models(parsed_data, image_detection)
        
        # 統合されたメタデータの作成
        integrated_metadata = self._integrate_metadata(
            parsed_data, 
            image_detection, 
            metadata_result
        )
        
        return {
            "content_models": content_models,
            "metadata": integrated_metadata,
            "parsed_data": parsed_data,
            "image_detection": image_detection,
            "validation": self._validate_conversion(content_models, parsed_data)
        }
    
    def _convert_to_content_models(
        self, 
        parsed_data: Dict[str, Any], 
        image_detection: Dict[str, Any]
    ) -> List[Content]:
        """パースデータをContentモデルに変換."""
        content_models = []
        structure = parsed_data["structure"]
        
        # チャプターの変換
        for chapter_data in structure["chapters"]:
            sections = []
            
            for section_data in chapter_data["sections"]:
                paragraphs = self._create_paragraphs_from_section(
                    section_data, 
                    parsed_data, 
                    image_detection
                )
                
                section = Section(
                    title=section_data["title"],
                    content=self._extract_section_summary(section_data),
                    learning_objectives=self._extract_learning_objectives(section_data),
                    paragraphs=paragraphs,
                    metadata={
                        "anchor": section_data["anchor"],
                        "line_number": section_data["line_number"],
                        "paragraph_count": len(paragraphs)
                    }
                )
                sections.append(section)
            
            chapter = Chapter(
                title=chapter_data["title"],
                content=self._extract_chapter_summary(chapter_data),
                sections=sections,
                metadata={
                    "anchor": chapter_data["anchor"],
                    "line_number": chapter_data["line_number"],
                    "section_count": len(sections)
                }
            )
            content_models.append(chapter)
        
        # セクションのみ（チャプターがない場合）
        for section_data in structure["sections"]:
            paragraphs = self._create_paragraphs_from_section(
                section_data, 
                parsed_data, 
                image_detection
            )
            
            section = Section(
                title=section_data["title"],
                content=self._extract_section_summary(section_data),
                learning_objectives=self._extract_learning_objectives(section_data),
                paragraphs=paragraphs,
                metadata={
                    "anchor": section_data["anchor"],
                    "line_number": section_data["line_number"],
                    "paragraph_count": len(paragraphs),
                    "standalone": True
                }
            )
            content_models.append(section)
        
        return content_models
    
    def _create_paragraphs_from_section(
        self, 
        section_data: Dict[str, Any], 
        parsed_data: Dict[str, Any], 
        image_detection: Dict[str, Any]
    ) -> List[Paragraph]:
        """セクションから段落を作成."""
        paragraphs = []
        
        # テキスト段落の作成
        text_paragraphs = self._extract_text_paragraphs(section_data, parsed_data)
        paragraphs.extend(text_paragraphs)
        
        # コードブロック段落の作成
        code_paragraphs = self._extract_code_paragraphs(section_data, parsed_data)
        paragraphs.extend(code_paragraphs)
        
        # 画像段落の作成
        image_paragraphs = self._extract_image_paragraphs(section_data, image_detection)
        paragraphs.extend(image_paragraphs)
        
        # 図表段落の作成
        diagram_paragraphs = self._extract_diagram_paragraphs(section_data, image_detection)
        paragraphs.extend(diagram_paragraphs)
        
        # 順序の調整
        paragraphs.sort(key=lambda p: p.metadata.get("source_line", 0))
        
        # order フィールドの更新
        for i, paragraph in enumerate(paragraphs):
            paragraph.order = i + 1
        
        return paragraphs
    
    def _extract_text_paragraphs(
        self, 
        section_data: Dict[str, Any], 
        parsed_data: Dict[str, Any]
    ) -> List[Paragraph]:
        """テキスト段落の抽出."""
        paragraphs = []
        
        # 段落コンテンツを探索（実装を簡略化）
        section_start = section_data.get("line_number", 0)
        
        # セクション内のテキストブロックを仮で作成
        # 実際の実装では、パースされた要素から適切に抽出する
        content_lines = parsed_data["content"].split('\n')
        
        current_paragraph = []
        paragraph_count = 0
        
        for i, line in enumerate(content_lines[section_start:], section_start):
            line_stripped = line.strip()
            
            # 見出しやコードブロックの開始で段落を区切る
            if (line_stripped.startswith('#') or 
                line_stripped.startswith('```') or
                line_stripped.startswith('![') or
                line_stripped.startswith('<img')):
                
                if current_paragraph:
                    paragraph_content = '\n'.join(current_paragraph).strip()
                    if paragraph_content:
                        paragraph = Paragraph(
                            title=f"段落{paragraph_count + 1}",
                            content=paragraph_content,
                            type="text",
                            order=paragraph_count + 1,
                            metadata={
                                "source_line": i - len(current_paragraph) + 1,
                                "line_count": len(current_paragraph)
                            }
                        )
                        paragraphs.append(paragraph)
                        paragraph_count += 1
                    current_paragraph = []
                continue
            
            # 空行で段落を区切る
            if not line_stripped:
                if current_paragraph:
                    paragraph_content = '\n'.join(current_paragraph).strip()
                    if paragraph_content:
                        paragraph = Paragraph(
                            title=f"段落{paragraph_count + 1}",
                            content=paragraph_content,
                            type="text",
                            order=paragraph_count + 1,
                            metadata={
                                "source_line": i - len(current_paragraph) + 1,
                                "line_count": len(current_paragraph)
                            }
                        )
                        paragraphs.append(paragraph)
                        paragraph_count += 1
                    current_paragraph = []
            else:
                current_paragraph.append(line)
        
        # 最後の段落
        if current_paragraph:
            paragraph_content = '\n'.join(current_paragraph).strip()
            if paragraph_content:
                paragraph = Paragraph(
                    title=f"段落{paragraph_count + 1}",
                    content=paragraph_content,
                    type="text",
                    order=paragraph_count + 1,
                    metadata={
                        "source_line": len(content_lines) - len(current_paragraph) + 1,
                        "line_count": len(current_paragraph)
                    }
                )
                paragraphs.append(paragraph)
        
        return paragraphs
    
    def _extract_code_paragraphs(
        self, 
        section_data: Dict[str, Any], 
        parsed_data: Dict[str, Any]
    ) -> List[Paragraph]:
        """コードブロック段落の抽出."""
        paragraphs = []
        section_start = section_data.get("line_number", 0)
        
        for code_block in parsed_data["code_blocks"]:
            # セクション範囲内のコードブロックのみ
            if code_block.line_number >= section_start:
                paragraph = Paragraph(
                    title=f"コードブロック ({code_block.language or 'plain'})",
                    content=code_block.content,
                    type="code",
                    order=0,  # 後で調整
                    metadata={
                        "language": code_block.language,
                        "source_line": code_block.line_number,
                        "filename": code_block.filename
                    }
                )
                paragraphs.append(paragraph)
        
        return paragraphs
    
    def _extract_image_paragraphs(
        self, 
        section_data: Dict[str, Any], 
        image_detection: Dict[str, Any]
    ) -> List[Paragraph]:
        """画像段落の抽出."""
        paragraphs = []
        section_start = section_data.get("line_number", 0)
        
        for image in image_detection["images"]:
            source_line = image.metadata.get("source_line", 0)
            
            # セクション範囲内の画像のみ
            if source_line >= section_start:
                paragraph = Paragraph(
                    title=image.alt_text or "画像",
                    content=f"![{image.alt_text}]({image.url})",
                    type="image",
                    order=0,  # 後で調整
                    metadata={
                        "image_url": image.url,
                        "alt_text": image.alt_text,
                        "title": image.title,
                        "image_type": image.image_type,
                        "is_local": image.is_local,
                        "exists": image.exists,
                        "source_line": source_line,
                        "size_info": image.size_info
                    }
                )
                paragraphs.append(paragraph)
        
        return paragraphs
    
    def _extract_diagram_paragraphs(
        self, 
        section_data: Dict[str, Any], 
        image_detection: Dict[str, Any]
    ) -> List[Paragraph]:
        """図表段落の抽出."""
        paragraphs = []
        section_start = section_data.get("line_number", 0)
        
        for diagram in image_detection["diagrams"]:
            # セクション範囲内の図表のみ
            if diagram.source_line >= section_start:
                paragraph = Paragraph(
                    title=diagram.title or f"{diagram.diagram_type.title()}図表",
                    content=diagram.content,
                    type="diagram",
                    order=0,  # 後で調整
                    metadata={
                        "diagram_type": diagram.diagram_type,
                        "language": diagram.language,
                        "description": diagram.description,
                        "source_line": diagram.source_line,
                        "line_count": diagram.metadata.get("line_count", 0)
                    }
                )
                paragraphs.append(paragraph)
        
        return paragraphs
    
    def _extract_section_summary(self, section_data: Dict[str, Any]) -> str:
        """セクションの概要を抽出."""
        # 実装を簡略化 - 実際にはセクションの最初の段落から抽出
        return f"{section_data['title']}に関する内容"
    
    def _extract_chapter_summary(self, chapter_data: Dict[str, Any]) -> str:
        """チャプターの概要を抽出."""
        # 実装を簡略化 - 実際にはチャプターの最初の段落から抽出
        return f"{chapter_data['title']}に関する章"
    
    def _extract_learning_objectives(self, section_data: Dict[str, Any]) -> List[str]:
        """学習目標の抽出."""
        # 実装を簡略化 - 実際にはセクション内の特定パターンから抽出
        objectives = []
        
        # "学習目標" "この章で学ぶこと" などのパターンを探す
        # ここでは仮の実装
        if "学習" in section_data.get("title", ""):
            objectives = [f"{section_data['title']}の習得"]
        
        return objectives
    
    def _integrate_metadata(
        self, 
        parsed_data: Dict[str, Any], 
        image_detection: Dict[str, Any], 
        metadata_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """統合メタデータの作成."""
        metadata = {}
        
        # front matterのメタデータ
        metadata.update(metadata_result.get("metadata", {}))
        
        # パース統計の追加
        validation_stats = parsed_data["validation"]["stats"]
        metadata.update({
            "content_statistics": {
                "word_count": validation_stats["word_count"],
                "character_count": validation_stats["character_count"],
                "total_lines": validation_stats["total_lines"],
                "heading_count": validation_stats["heading_count"],
                "code_block_count": validation_stats["code_block_count"]
            }
        })
        
        # 画像統計の追加
        image_summary = image_detection["summary"]
        metadata.update({
            "image_statistics": {
                "total_images": image_summary["total_images"],
                "local_images": image_summary["local_images"],
                "remote_images": image_summary["remote_images"],
                "missing_images": image_summary["missing_images"],
                "total_diagrams": image_summary["total_diagrams"],
                "diagram_types": image_summary["diagram_types"]
            }
        })
        
        # 構造統計の追加
        structure = parsed_data["structure"]
        metadata.update({
            "structure_statistics": {
                "chapter_count": len(structure["chapters"]),
                "section_count": sum(len(ch["sections"]) for ch in structure["chapters"]),
                "max_heading_level": max(
                    (h.level for h in self.markdown_parser.headings), 
                    default=0
                )
            }
        })
        
        return metadata
    
    def _validate_conversion(
        self, 
        content_models: List[Content], 
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """変換結果のバリデーション."""
        errors = []
        warnings = []
        
        # 基本チェック
        if not content_models:
            errors.append("No content models were created")
        
        # 各コンテンツモデルのチェック
        for i, model in enumerate(content_models):
            if not model.title:
                errors.append(f"Content model {i} has no title")
            
            if isinstance(model, Chapter):
                if not model.sections:
                    warnings.append(f"Chapter '{model.title}' has no sections")
                
                for j, section in enumerate(model.sections):
                    if not section.paragraphs:
                        warnings.append(f"Section '{section.title}' in chapter '{model.title}' has no paragraphs")
            
            elif isinstance(model, Section):
                if not model.paragraphs:
                    warnings.append(f"Section '{model.title}' has no paragraphs")
        
        # 構造の整合性チェック
        markdown_headings = len(self.markdown_parser.headings)
        created_sections = sum(
            len(model.sections) if isinstance(model, Chapter) else 1 
            for model in content_models
        )
        
        if created_sections != markdown_headings:
            warnings.append(
                f"Section count mismatch: {created_sections} sections created "
                f"but {markdown_headings} headings found"
            )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "statistics": {
                "content_models_created": len(content_models),
                "chapters": sum(1 for m in content_models if isinstance(m, Chapter)),
                "standalone_sections": sum(1 for m in content_models if isinstance(m, Section)),
                "total_paragraphs": sum(
                    len(m.sections) if isinstance(m, Chapter) 
                    else len(m.paragraphs) if isinstance(m, Section) 
                    else 0 
                    for m in content_models
                )
            }
        } 