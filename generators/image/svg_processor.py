"""
SVG画像の処理を担当するモジュール。
SVG画像のPNG変換や最適化機能を提供する。
"""
import os
import re
from typing import Optional

# SVG to PNG変換ライブラリ
try:
    import cairosvg
except ImportError:
    cairosvg = None


class SVGProcessor:
    """
    SVG画像処理クラス。
    SVG形式の画像をPNG形式に変換する機能を提供する。
    """
    
    def __init__(self):
        """SVGProcessorを初期化する。"""
        # cairosvgの可用性チェック
        if cairosvg is None:
            print("警告: cairosvgモジュールがインストールされていません。SVG変換機能が制限されます。")
    
    def process_image(self, content: str, output_path: str) -> str:
        """
        SVG画像を処理し、PNG形式に変換する。
        
        Args:
            content (str): SVG画像のコンテンツ（XMLテキスト）
            output_path (str): 出力ファイルパス
        
        Returns:
            str: 処理されたPNG画像のパス
        
        Raises:
            ValueError: SVG処理中にエラーが発生した場合
        """
        try:
            # SVGコンテンツを最適化
            optimized_svg = self.optimize_svg(content)
            
            # 出力ディレクトリが存在することを確認
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # SVGをPNGに変換
            if cairosvg:
                cairosvg.svg2png(bytestring=optimized_svg.encode('utf-8'), write_to=output_path)
            else:
                # cairosvgが利用できない場合は、代替方法を試みる
                self._fallback_conversion(optimized_svg, output_path)
            
            return output_path
            
        except Exception as e:
            raise ValueError(f"SVG処理エラー: {str(e)}")
    
    def optimize_svg(self, content: str) -> str:
        """
        SVGコンテンツを最適化する。
        不要なコメントやメタデータを削除し、要素を整理する。
        
        Args:
            content (str): 最適化するSVGコンテンツ
        
        Returns:
            str: 最適化されたSVGコンテンツ
        """
        # コメントを削除
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # 余分な空白を削除
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'> <', '><', content)
        
        # 空の要素を削除（オプション）
        # content = re.sub(r'<rect[^>]*width="0"[^>]*height="0"[^>]*/?>', '', content)
        
        return content
    
    def _fallback_conversion(self, svg_content: str, output_path: str) -> None:
        """
        cairosvgが利用できない場合の代替変換メソッド。
        
        Args:
            svg_content (str): SVGコンテンツ
            output_path (str): 出力ファイルパス
        
        Raises:
            ValueError: 代替変換方法が利用できない場合
        """
        # 一時的なSVGファイルを作成
        temp_svg_path = output_path.replace('.png', '.svg')
        with open(temp_svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        # 外部コマンドを使った変換を試みる
        try:
            import subprocess
            # Inkscapeを使用した変換を試みる
            subprocess.run(['inkscape', '-z', '-e', output_path, temp_svg_path], 
                          check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 一時ファイルを削除
            if os.path.exists(temp_svg_path):
                os.remove(temp_svg_path)
                
            return
        except (subprocess.SubprocessError, ImportError, FileNotFoundError):
            pass
        
        # その他の代替方法（例：ImageMagick）
        try:
            import subprocess
            subprocess.run(['convert', temp_svg_path, output_path], 
                          check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 一時ファイルを削除
            if os.path.exists(temp_svg_path):
                os.remove(temp_svg_path)
                
            return
        except (subprocess.SubprocessError, ImportError, FileNotFoundError):
            # 一時ファイルを削除
            if os.path.exists(temp_svg_path):
                os.remove(temp_svg_path)
            
            # 他の方法が見つからない場合
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("PNG conversion failed. Original SVG content:")
                f.write(svg_content)
            
            raise ValueError("SVG変換に必要なライブラリまたはツールがインストールされていません。"
                            "cairosvg、Inkscape、またはImageMagickをインストールしてください。") 