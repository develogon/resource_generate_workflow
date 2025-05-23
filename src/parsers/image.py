"""画像・図表検出システム."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..config.constants import IMAGE_EXTENSIONS


@dataclass
class DetectedImage:
    """検出された画像情報."""
    
    alt_text: str
    url: str
    title: str = ""
    image_type: str = "unknown"
    file_extension: str = ""
    is_local: bool = True
    exists: bool = False
    size_info: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の処理."""
        if self.url:
            # ファイル拡張子の抽出
            url_lower = self.url.lower()
            for ext in IMAGE_EXTENSIONS:
                if url_lower.endswith(ext):
                    self.file_extension = ext
                    break
            
            # ローカル/リモートの判定
            self.is_local = not (
                self.url.startswith('http://') or 
                self.url.startswith('https://') or
                self.url.startswith('//')
            )
            
            # 画像タイプの判定
            self.image_type = self._determine_image_type()
    
    def _determine_image_type(self) -> str:
        """画像タイプの判定."""
        url_lower = self.url.lower()
        
        # 拡張子ベースの判定
        if self.file_extension:
            if self.file_extension in ['.jpg', '.jpeg']:
                return 'photo'
            elif self.file_extension in ['.png']:
                return 'diagram'
            elif self.file_extension in ['.svg']:
                return 'vector'
            elif self.file_extension in ['.gif']:
                return 'animation'
            elif self.file_extension in ['.webp']:
                return 'modern'
        
        # URL・alt textベースの判定
        diagram_keywords = ['diagram', 'chart', 'graph', 'flow', 'architecture', 'structure']
        screenshot_keywords = ['screenshot', 'capture', 'screen']
        
        combined_text = f"{self.url} {self.alt_text}".lower()
        
        if any(keyword in combined_text for keyword in diagram_keywords):
            return 'diagram'
        elif any(keyword in combined_text for keyword in screenshot_keywords):
            return 'screenshot'
        
        return 'unknown'


@dataclass
class DetectedDiagram:
    """検出された図表情報."""
    
    diagram_type: str
    content: str
    language: str = ""
    title: str = ""
    description: str = ""
    source_line: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ImageDetector:
    """画像検出システム."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """初期化."""
        self.base_path = base_path or Path('.')
        self.detected_images: List[DetectedImage] = []
        self.detected_diagrams: List[DetectedDiagram] = []
    
    def detect_in_content(self, content: str, base_path: Optional[Path] = None) -> Dict[str, Any]:
        """コンテンツ内の画像・図表を検出."""
        if base_path:
            self.base_path = base_path
        
        self.detected_images.clear()
        self.detected_diagrams.clear()
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_number = i + 1
            
            # Markdown画像の検出
            self._detect_markdown_images(line, line_number)
            
            # HTML画像の検出
            self._detect_html_images(line, line_number)
            
            # Mermaid図表の検出
            if line.strip().startswith('```mermaid'):
                diagram = self._extract_code_block_diagram(lines, i, 'mermaid')
                if diagram:
                    self.detected_diagrams.append(diagram)
            
            # PlantUML図表の検出
            elif line.strip().startswith('```plantuml'):
                diagram = self._extract_code_block_diagram(lines, i, 'plantuml')
                if diagram:
                    self.detected_diagrams.append(diagram)
            
            # Graphviz図表の検出
            elif line.strip().startswith('```dot') or line.strip().startswith('```graphviz'):
                diagram = self._extract_code_block_diagram(lines, i, 'graphviz')
                if diagram:
                    self.detected_diagrams.append(diagram)
        
        # ローカル画像の存在確認
        self._verify_local_images()
        
        return {
            "images": self.detected_images,
            "diagrams": self.detected_diagrams,
            "summary": {
                "total_images": len(self.detected_images),
                "local_images": sum(1 for img in self.detected_images if img.is_local),
                "remote_images": sum(1 for img in self.detected_images if not img.is_local),
                "existing_images": sum(1 for img in self.detected_images if img.exists),
                "missing_images": sum(1 for img in self.detected_images if img.is_local and not img.exists),
                "total_diagrams": len(self.detected_diagrams),
                "diagram_types": list(set(d.diagram_type for d in self.detected_diagrams))
            }
        }
    
    def _detect_markdown_images(self, line: str, line_number: int) -> None:
        """Markdown形式の画像を検出."""
        # ![alt](url "title") パターン
        pattern = r'!\[([^\]]*)\]\(([^)]+?)(?:\s+"([^"]*)")?\)'
        
        for match in re.finditer(pattern, line):
            alt_text = match.group(1)
            url = match.group(2).strip()
            title = match.group(3) or ""
            
            image = DetectedImage(
                alt_text=alt_text,
                url=url,
                title=title,
                metadata={
                    "source_line": line_number,
                    "format": "markdown",
                    "raw_match": match.group(0)
                }
            )
            
            self.detected_images.append(image)
    
    def _detect_html_images(self, line: str, line_number: int) -> None:
        """HTML形式の画像を検出."""
        # <img> タグパターン
        pattern = r'<img[^>]*?src\s*=\s*["\']([^"\']+)["\'][^>]*?(?:alt\s*=\s*["\']([^"\']*)["\'][^>]*?)?>'
        
        for match in re.finditer(pattern, line, re.IGNORECASE):
            url = match.group(1)
            alt_text = match.group(2) or ""
            
            # title属性の抽出
            title_match = re.search(r'title\s*=\s*["\']([^"\']*)["\']', match.group(0), re.IGNORECASE)
            title = title_match.group(1) if title_match else ""
            
            image = DetectedImage(
                alt_text=alt_text,
                url=url,
                title=title,
                metadata={
                    "source_line": line_number,
                    "format": "html",
                    "raw_match": match.group(0)
                }
            )
            
            self.detected_images.append(image)
    
    def _extract_code_block_diagram(self, lines: List[str], start_index: int, diagram_type: str) -> Optional[DetectedDiagram]:
        """コードブロック形式の図表を抽出."""
        if start_index >= len(lines):
            return None
        
        content_lines = []
        i = start_index + 1
        
        # ```で終わるまでの内容を取得
        while i < len(lines):
            line = lines[i]
            if line.strip() == '```':
                break
            content_lines.append(line)
            i += 1
        
        if not content_lines:
            return None
        
        content = '\n'.join(content_lines)
        
        # タイトルの抽出（最初のコメント行から）
        title = ""
        description = ""
        
        if diagram_type == 'mermaid':
            # Mermaidのタイトル抽出
            title_match = re.search(r'title\s+(.+)', content)
            if title_match:
                title = title_match.group(1).strip()
        
        return DetectedDiagram(
            diagram_type=diagram_type,
            content=content,
            title=title,
            description=description,
            source_line=start_index + 1,
            metadata={
                "language": diagram_type,
                "line_count": len(content_lines)
            }
        )
    
    def _verify_local_images(self) -> None:
        """ローカル画像の存在を確認."""
        for image in self.detected_images:
            if image.is_local:
                # 相対パスを絶対パスに変換
                if image.url.startswith('/'):
                    # 絶対パス
                    image_path = Path(image.url)
                else:
                    # 相対パス
                    image_path = self.base_path / image.url
                
                image.exists = image_path.exists()
                
                if image.exists and image_path.is_file():
                    try:
                        # ファイルサイズ情報を取得
                        stat = image_path.stat()
                        image.size_info = {
                            "file_size": stat.st_size,
                            "file_size_mb": round(stat.st_size / (1024 * 1024), 2)
                        }
                        
                        # 画像メタデータの取得（PILが利用可能な場合）
                        try:
                            from PIL import Image
                            with Image.open(image_path) as img:
                                image.size_info.update({
                                    "width": img.width,
                                    "height": img.height,
                                    "format": img.format,
                                    "mode": img.mode
                                })
                        except ImportError:
                            # PILが利用できない場合はファイルサイズのみ
                            pass
                        except Exception:
                            # 画像ファイルの読み込みに失敗した場合
                            pass
                            
                    except Exception:
                        # ファイル情報の取得に失敗
                        pass
    
    def analyze_image_usage(self) -> Dict[str, Any]:
        """画像使用状況の分析."""
        if not self.detected_images:
            return {"message": "No images detected"}
        
        # タイプ別統計
        type_stats = {}
        for image in self.detected_images:
            img_type = image.image_type
            if img_type not in type_stats:
                type_stats[img_type] = 0
            type_stats[img_type] += 1
        
        # 拡張子別統計
        ext_stats = {}
        for image in self.detected_images:
            ext = image.file_extension or 'unknown'
            if ext not in ext_stats:
                ext_stats[ext] = 0
            ext_stats[ext] += 1
        
        # サイズ統計（ローカル画像のみ）
        total_size = 0
        size_count = 0
        large_images = []
        
        for image in self.detected_images:
            if image.size_info and "file_size" in image.size_info:
                file_size = image.size_info["file_size"]
                total_size += file_size
                size_count += 1
                
                # 1MB以上の画像を大きいファイルとして記録
                if file_size > 1024 * 1024:
                    large_images.append({
                        "url": image.url,
                        "size_mb": image.size_info["file_size_mb"],
                        "alt_text": image.alt_text
                    })
        
        return {
            "total_images": len(self.detected_images),
            "type_distribution": type_stats,
            "extension_distribution": ext_stats,
            "local_vs_remote": {
                "local": sum(1 for img in self.detected_images if img.is_local),
                "remote": sum(1 for img in self.detected_images if not img.is_local)
            },
            "existence_status": {
                "existing": sum(1 for img in self.detected_images if img.exists),
                "missing": sum(1 for img in self.detected_images if img.is_local and not img.exists),
                "remote": sum(1 for img in self.detected_images if not img.is_local)
            },
            "size_analysis": {
                "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size > 0 else 0,
                "average_size_mb": round(total_size / (1024 * 1024) / size_count, 2) if size_count > 0 else 0,
                "large_images": large_images
            },
            "accessibility": {
                "with_alt_text": sum(1 for img in self.detected_images if img.alt_text.strip()),
                "without_alt_text": sum(1 for img in self.detected_images if not img.alt_text.strip()),
                "with_title": sum(1 for img in self.detected_images if img.title.strip())
            }
        }
    
    def get_optimization_suggestions(self) -> List[str]:
        """最適化提案を生成."""
        suggestions = []
        
        # 不足しているalt textの警告
        missing_alt = sum(1 for img in self.detected_images if not img.alt_text.strip())
        if missing_alt > 0:
            suggestions.append(f"{missing_alt}個の画像にalt textが設定されていません。アクセシビリティのために追加してください。")
        
        # 存在しない画像の警告
        missing_files = sum(1 for img in self.detected_images if img.is_local and not img.exists)
        if missing_files > 0:
            suggestions.append(f"{missing_files}個のローカル画像ファイルが見つかりません。パスを確認してください。")
        
        # 大きなファイルサイズの警告
        large_images = [img for img in self.detected_images 
                       if img.size_info and img.size_info.get("file_size", 0) > 5 * 1024 * 1024]
        if large_images:
            suggestions.append(f"{len(large_images)}個の画像が5MB以上です。圧縮を検討してください。")
        
        # 非効率な形式の警告
        inefficient_formats = sum(1 for img in self.detected_images 
                                 if img.file_extension in ['.bmp', '.tiff'])
        if inefficient_formats > 0:
            suggestions.append(f"{inefficient_formats}個の画像が非効率な形式です。JPEGやPNGに変換を検討してください。")
        
        return suggestions 