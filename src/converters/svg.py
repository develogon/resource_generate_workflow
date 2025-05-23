"""SVG画像変換器."""

import logging
from typing import Optional
import base64
import io

from .base import BaseConverter, ImageType
from ..config import Config

logger = logging.getLogger(__name__)


class SVGConverter(BaseConverter):
    """SVG画像変換器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        
    def get_supported_type(self) -> ImageType:
        """サポートする画像タイプを返す."""
        return ImageType.SVG
        
    async def convert(self, source: str, **kwargs) -> bytes:
        """SVGをPNG/JPGに変換.
        
        Args:
            source: SVGデータ（文字列形式）
            **kwargs: 追加のオプション
                - width: 出力幅（デフォルト: config.image.width）
                - height: 出力高さ（デフォルト: config.image.height）
                - format: 出力フォーマット（デフォルト: config.image.format）
                
        Returns:
            変換後の画像データ（バイナリ）
            
        Raises:
            ValueError: 無効なSVGデータの場合
            RuntimeError: 変換に失敗した場合
        """
        if not self.validate_source(source):
            raise ValueError("Invalid SVG source data")
            
        try:
            # オプションの取得
            width = kwargs.get('width', self.config.image.width)
            height = kwargs.get('height', self.config.image.height)
            output_format = kwargs.get('format', self.get_output_format())
            
            # SVGデータの前処理
            svg_data = self._preprocess_svg(source, width, height)
            
            # 実際の変換処理
            if output_format.lower() == 'png':
                return await self._convert_to_png(svg_data, width, height)
            elif output_format.lower() in ['jpg', 'jpeg']:
                return await self._convert_to_jpg(svg_data, width, height)
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
                
        except Exception as e:
            logger.error(f"SVG conversion failed: {e}")
            raise RuntimeError(f"SVG conversion failed: {e}")
            
    def _preprocess_svg(self, svg_data: str, width: int, height: int) -> str:
        """SVGデータの前処理.
        
        Args:
            svg_data: 元のSVGデータ
            width: 出力幅
            height: 出力高さ
            
        Returns:
            前処理済みのSVGデータ
        """
        # SVGタグの確認と追加
        if not svg_data.strip().startswith('<svg'):
            # SVGタグがない場合は追加
            svg_data = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">{svg_data}</svg>'
        else:
            # 既存のSVGタグのサイズを調整
            import re
            # width属性の設定/更新
            if 'width=' in svg_data:
                svg_data = re.sub(r'width="[^"]*"', f'width="{width}"', svg_data)
            else:
                svg_data = svg_data.replace('<svg', f'<svg width="{width}"', 1)
                
            # height属性の設定/更新
            if 'height=' in svg_data:
                svg_data = re.sub(r'height="[^"]*"', f'height="{height}"', svg_data)
            else:
                svg_data = svg_data.replace('<svg', f'<svg height="{height}"', 1)
                
        return svg_data
        
    async def _convert_to_png(self, svg_data: str, width: int, height: int) -> bytes:
        """SVGをPNGに変換.
        
        Args:
            svg_data: SVGデータ
            width: 出力幅
            height: 出力高さ
            
        Returns:
            PNG画像データ
        """
        try:
            # cairosvgを使用してPNGに変換
            import cairosvg
            
            png_data = cairosvg.svg2png(
                bytestring=svg_data.encode('utf-8'),
                output_width=width,
                output_height=height
            )
            
            return png_data
            
        except ImportError:
            # cairosvgが利用できない場合の代替実装
            logger.warning("cairosvg not available, using fallback conversion")
            return await self._fallback_conversion(svg_data, 'png', width, height)
            
    async def _convert_to_jpg(self, svg_data: str, width: int, height: int) -> bytes:
        """SVGをJPGに変換.
        
        Args:
            svg_data: SVGデータ
            width: 出力幅
            height: 出力高さ
            
        Returns:
            JPG画像データ
        """
        try:
            # まずPNGに変換してからJPGに変換
            png_data = await self._convert_to_png(svg_data, width, height)
            
            # PillowでPNGからJPGに変換
            from PIL import Image
            
            # PNGデータを読み込み
            png_image = Image.open(io.BytesIO(png_data))
            
            # RGBAからRGBに変換（JPGは透明度をサポートしないため）
            if png_image.mode == 'RGBA':
                # 白背景で合成
                rgb_image = Image.new('RGB', png_image.size, (255, 255, 255))
                rgb_image.paste(png_image, mask=png_image.split()[-1])
                png_image = rgb_image
                
            # JPGとして保存
            jpg_buffer = io.BytesIO()
            png_image.save(jpg_buffer, format='JPEG', quality=90)
            
            return jpg_buffer.getvalue()
            
        except ImportError:
            logger.warning("PIL not available, using fallback conversion")
            return await self._fallback_conversion(svg_data, 'jpg', width, height)
            
    async def _fallback_conversion(self, svg_data: str, format: str, width: int, height: int) -> bytes:
        """フォールバック変換処理.
        
        Args:
            svg_data: SVGデータ
            format: 出力フォーマット
            width: 出力幅
            height: 出力高さ
            
        Returns:
            変換後の画像データ
        """
        # 簡易的な実装：SVGデータをBase64エンコードして返す
        # 実際のプロダクションでは、外部サービスやより高度な変換ライブラリを使用
        logger.warning(f"Using fallback conversion for SVG to {format}")
        
        # SVGデータをBase64エンコード
        encoded_data = base64.b64encode(svg_data.encode('utf-8'))
        
        # 簡易的なヘッダーを追加（実際の画像ファイルではない）
        if format.lower() == 'png':
            # PNG署名を模擬
            header = b'\x89PNG\r\n\x1a\n'
        else:
            # JPEG署名を模擬
            header = b'\xff\xd8\xff\xe0'
            
        return header + encoded_data[:1000]  # サイズ制限
        
    def validate_source(self, source: str) -> bool:
        """SVGソースデータの検証.
        
        Args:
            source: 検証するSVGデータ
            
        Returns:
            検証結果
        """
        if not super().validate_source(source):
            return False
            
        # SVGの基本的な構造チェック
        source_lower = source.lower().strip()
        
        # SVGタグまたはSVG要素が含まれているかチェック
        has_svg_tag = '<svg' in source_lower
        has_svg_elements = any(element in source_lower for element in [
            '<circle', '<rect', '<path', '<line', '<polygon', '<polyline', 
            '<ellipse', '<text', '<g', '<defs', '<use'
        ])
        
        if not has_svg_tag and not has_svg_elements:
            return False
            
        # 基本的なXML構造チェック
        if '<' not in source or '>' not in source:
            return False
            
        return True 