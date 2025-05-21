"""
Draw.io XML図の処理を担当するモジュール。
Draw.io XML図のPNG変換や解析機能を提供する。
"""
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict


class DrawIOProcessor:
    """
    Draw.io XML図処理クラス。
    Draw.io XML形式の図をPNG形式に変換する機能を提供する。
    """
    
    def __init__(self):
        """DrawIOProcessorを初期化する。"""
        # Draw.io CLIの可用性チェック
        self.drawio_cli_available = self._check_drawio_cli()
    
    def process_image(self, content: str, output_path: str) -> str:
        """
        Draw.io XML図を処理し、PNG形式に変換する。
        
        Args:
            content (str): Draw.io XML図のコンテンツ（XMLテキスト）
            output_path (str): 出力ファイルパス
        
        Returns:
            str: 処理されたPNG画像のパス
        
        Raises:
            ValueError: Draw.io XML処理中にエラーが発生した場合
        """
        try:
            # 出力ディレクトリが存在することを確認
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 一時ファイルを作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.drawio', delete=False) as temp_file:
                temp_drawio_path = temp_file.name
                temp_file.write(content)
            
            # ページIDの取得（複数のダイアグラムがある場合）
            page_id = self.get_page_id(content)
            
            # Draw.io XMLをPNGに変換
            if self.drawio_cli_available:
                self._convert_with_drawio_cli(temp_drawio_path, output_path, page_id)
            else:
                # 代替方法を試みる
                self._fallback_conversion(content, output_path)
            
            # 一時ファイルを削除
            if os.path.exists(temp_drawio_path):
                os.remove(temp_drawio_path)
            
            return output_path
            
        except Exception as e:
            # 一時ファイルのクリーンアップ
            if 'temp_drawio_path' in locals() and os.path.exists(temp_drawio_path):
                os.remove(temp_drawio_path)
            
            raise ValueError(f"Draw.io XML処理エラー: {str(e)}")
    
    def get_page_id(self, content: str) -> Optional[str]:
        """
        Draw.io XMLからページID（複数のダイアグラムがある場合）を取得する。
        
        Args:
            content (str): Draw.io XMLコンテンツ
        
        Returns:
            Optional[str]: ページID、または単一ページの場合はNone
        """
        try:
            # XMLを解析
            root = ET.fromstring(content)
            
            # ページ（ダイアグラム）のIDを取得
            diagrams = root.findall('./diagram')
            
            if not diagrams:
                # ダイアグラムがない場合
                return None
            
            # 最初のダイアグラムのIDを使用（ダイアグラムが1つでもIDを返す）
            return diagrams[0].get('id')
            
        except Exception:
            # XML解析エラーの場合はNoneを返す
            return None
    
    def _check_drawio_cli(self) -> bool:
        """
        Draw.io CLIの可用性をチェックする。
        
        Returns:
            bool: Draw.io CLIが利用可能な場合はTrue、そうでない場合はFalse
        """
        # 複数の可能性のあるコマンド名をチェック
        possible_commands = ['drawio', 'draw.io', 'diagrams.net']
        
        for cmd in possible_commands:
            try:
                result = subprocess.run([cmd, '--help'], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, 
                                      check=False)
                if result.returncode == 0:
                    return True
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
                
        return False
    
    def _convert_with_drawio_cli(self, input_path: str, output_path: str, page_id: Optional[str] = None) -> None:
        """
        Draw.io CLIを使用してDraw.io XMLをPNGに変換する。
        
        Args:
            input_path (str): 入力Draw.io XMLファイルのパス
            output_path (str): 出力PNGファイルのパス
            page_id (Optional[str]): 特定のページID（複数のダイアグラムがある場合）
        
        Raises:
            ValueError: 変換中にエラーが発生した場合
        """
        try:
            # 使用するコマンドを決定
            command = None
            for cmd in ['drawio', 'draw.io', 'diagrams.net']:
                try:
                    subprocess.run([cmd, '--version'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  check=False)
                    command = cmd
                    break
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
            
            if not command:
                raise ValueError("Draw.io CLIが見つかりません")
            
            # コマンドライン引数の構築
            cmd_args = [command, '--export', '--format', 'png', '--output', output_path, input_path]
            
            # 特定のページIDがある場合は追加
            if page_id:
                cmd_args.extend(['--page-index', page_id])
            
            # Draw.io CLIコマンドを実行
            result = subprocess.run(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            # 出力ファイルが生成されたか確認
            if not os.path.exists(output_path):
                raise ValueError("Draw.io CLIコマンドは成功しましたが、出力ファイルが生成されませんでした")
                
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode('utf-8') if e.stderr else "不明なエラー"
            raise ValueError(f"Draw.io CLIコマンド実行エラー: {error_message}")
    
    def _fallback_conversion(self, content: str, output_path: str) -> None:
        """
        Draw.io CLIが利用できない場合の代替変換メソッド。
        
        Args:
            content (str): Draw.io XML内容
            output_path (str): 出力ファイルパス
        
        Raises:
            ValueError: 代替変換方法が利用できない場合
        """
        # Python librsvgとcairoを使用した代替方法
        try:
            import cairo
            import rsvg
            
            # SVGに変換
            svg_content = self._convert_to_svg(content)
            if svg_content:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as temp_file:
                    temp_svg_path = temp_file.name
                    temp_file.write(svg_content)
                
                # SVGからPNGに変換
                svg = rsvg.Handle(file=temp_svg_path)
                width, height = svg.get_dimension_data()[:2]
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
                context = cairo.Context(surface)
                svg.render_cairo(context)
                surface.write_to_png(output_path)
                
                # 一時ファイルを削除
                if os.path.exists(temp_svg_path):
                    os.remove(temp_svg_path)
                
                return
        except ImportError:
            pass
        
        # その他の代替方法がない場合
        # XMLファイルとして保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Draw.io Diagram (PNG conversion not available)\n\n")
            f.write("Please open this content in Draw.io (https://app.diagrams.net/)\n\n")
            f.write(content)
        
        # レポート用のエラーメッセージを表示
        print("警告: Draw.io図のPNG変換ができませんでした。Draw.io CLIをインストールしてください。")
    
    def _convert_to_svg(self, xml_content: str) -> Optional[str]:
        """
        Draw.io XMLをSVGに変換する試み（ライブラリがない場合は失敗）
        
        Args:
            xml_content (str): Draw.io XML内容
        
        Returns:
            Optional[str]: 変換されたSVG内容、または変換できない場合はNone
        """
        # 単純な方法としてXMLからSVGに変換する部分だけ抽出
        try:
            svg_match = re.search(r'<svg[^>]*>.*?</svg>', xml_content, re.DOTALL)
            if svg_match:
                return svg_match.group(0)
        except Exception:
            pass
            
        return None 