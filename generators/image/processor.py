"""
画像処理を担当する基底モジュール。
異なるタイプの画像フォーマットに対応するプロセッサを提供する。
"""
import re
from typing import Optional, Any


class ImageProcessor:
    """
    画像処理の基底クラス。
    異なる画像タイプのファクトリーとディスパッチャーとして機能する。
    """
    
    def __init__(self):
        """ImageProcessorを初期化する。"""
        pass
    
    def detect_image_type(self, content: str) -> str:
        """
        コンテンツからイメージタイプを検出する。
        
        Args:
            content (str): 画像コンテンツのテキスト表現
        
        Returns:
            str: 検出された画像タイプ (svg, mermaid, drawio, unknown)
        """
        content = content.strip()
        
        # SVGの検出
        if content.startswith('<svg') or '<svg xmlns' in content:
            return "svg"
        
        # Mermaidの検出
        if (content.startswith('graph ') or 
            content.startswith('sequenceDiagram') or 
            content.startswith('classDiagram') or 
            content.startswith('stateDiagram') or 
            content.startswith('flowchart') or 
            content.startswith('pie') or 
            content.startswith('gantt')):
            return "mermaid"
        
        # Draw.ioの検出
        if '<mxfile' in content or '<mxGraphModel' in content:
            return "drawio"
        
        # タイプが不明
        return "unknown"
    
    def get_processor(self, image_type: str) -> Any:
        """
        指定された画像タイプに適したプロセッサを取得する。
        
        Args:
            image_type (str): 画像タイプ (svg, mermaid, drawio)
        
        Returns:
            Any: 指定された画像タイプのプロセッサインスタンス
        
        Raises:
            ValueError: サポートされていない画像タイプの場合
        """
        if image_type == "svg":
            from generators.image.svg_processor import SVGProcessor
            return SVGProcessor()
        elif image_type == "mermaid":
            from generators.image.mermaid_processor import MermaidProcessor
            return MermaidProcessor()
        elif image_type == "drawio":
            from generators.image.drawio_processor import DrawIOProcessor
            return DrawIOProcessor()
        else:
            raise ValueError(f"サポートされていない画像タイプです: {image_type}")
    
    def process_image(self, content: str, output_path: str) -> str:
        """
        画像コンテンツを処理する。
        画像タイプを検出し、適切なプロセッサにディスパッチする。
        
        Args:
            content (str): 画像コンテンツのテキスト表現
            output_path (str): 出力ファイルパス
        
        Returns:
            str: 処理された画像のパス
        
        Raises:
            ValueError: サポートされていない画像タイプの場合
        """
        # 画像タイプを検出
        image_type = self.detect_image_type(content)
        
        if image_type == "unknown":
            raise ValueError("画像タイプを検出できませんでした")
        
        # 適切なプロセッサを取得
        processor = self.get_processor(image_type)
        
        # 画像を処理
        return processor.process_image(content, output_path) 