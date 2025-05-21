"""
Mermaid図の処理を担当するモジュール。
Mermaid図のPNG変換や検証機能を提供する。
"""
import os
import re
import subprocess
import tempfile
from typing import Optional, Tuple


class MermaidProcessor:
    """
    Mermaid図処理クラス。
    Mermaid形式の図をPNG形式に変換する機能を提供する。
    """
    
    def __init__(self):
        """MermaidProcessorを初期化する。"""
        # mmdc（Mermaid CLI）の可用性チェック
        self.mmdc_available = self._check_mmdc()
    
    def process_image(self, content: str, output_path: str) -> str:
        """
        Mermaid図を処理し、PNG形式に変換する。
        
        Args:
            content (str): Mermaid図のコンテンツ（テキスト）
            output_path (str): 出力ファイルパス
        
        Returns:
            str: 処理されたPNG画像のパス
        
        Raises:
            ValueError: Mermaid処理中にエラーが発生した場合
        """
        try:
            # Mermaid構文を検証
            if not self.validate_syntax(content):
                raise ValueError("Mermaid構文に問題があります")
            
            # 出力ディレクトリが存在することを確認
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 一時ファイルを作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp_file:
                temp_mermaid_path = temp_file.name
                temp_file.write(content)
            
            # Mermaid図をPNGに変換
            if self.mmdc_available:
                self._convert_with_mmdc(temp_mermaid_path, output_path)
            else:
                # 代替方法を試みる
                self._fallback_conversion(content, output_path)
            
            # 一時ファイルを削除
            if os.path.exists(temp_mermaid_path):
                os.remove(temp_mermaid_path)
            
            return output_path
            
        except Exception as e:
            # 一時ファイルのクリーンアップ
            if 'temp_mermaid_path' in locals() and os.path.exists(temp_mermaid_path):
                os.remove(temp_mermaid_path)
            
            raise ValueError(f"Mermaid処理エラー: {str(e)}")
    
    def validate_syntax(self, content: str) -> bool:
        """
        Mermaid構文を検証する。
        
        Args:
            content (str): 検証するMermaid構文
        
        Returns:
            bool: 構文が有効な場合はTrue、そうでない場合はFalse
        """
        # 基本的なバリデーション
        if not content or not content.strip():
            return False
        
        # 基本的な構文パターンのチェック
        valid_starts = ['graph ', 'flowchart ', 'sequenceDiagram', 'classDiagram', 
                       'stateDiagram', 'gantt', 'pie', 'journey']
        
        content_lines = content.strip().split('\n')
        if not content_lines:
            return False
        
        first_line = content_lines[0].strip()
        for valid_start in valid_starts:
            if first_line.startswith(valid_start):
                return True
        
        # その他の一般的なエラーチェック
        # 括弧の不一致など
        
        return False
    
    def _check_mmdc(self) -> bool:
        """
        mmdc（Mermaid CLI）の可用性をチェックする。
        
        Returns:
            bool: mmdc が利用可能な場合はTrue、そうでない場合はFalse
        """
        try:
            result = subprocess.run(['mmdc', '--version'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  check=False)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _convert_with_mmdc(self, input_path: str, output_path: str) -> None:
        """
        mmdc（Mermaid CLI）を使用してMermaid図をPNGに変換する。
        
        Args:
            input_path (str): 入力Mermaidファイルのパス
            output_path (str): 出力PNGファイルのパス
        
        Raises:
            ValueError: 変換中にエラーが発生した場合
        """
        try:
            # mmdc コマンドを実行
            result = subprocess.run(
                ['mmdc', '-i', input_path, '-o', output_path, '-t', 'neutral', '-b', 'transparent'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            
            # 出力ファイルが生成されたか確認
            if not os.path.exists(output_path):
                raise ValueError("mmdc コマンドは成功しましたが、出力ファイルが生成されませんでした")
                
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode('utf-8') if e.stderr else "不明なエラー"
            raise ValueError(f"mmdc コマンド実行エラー: {error_message}")
    
    def _fallback_conversion(self, content: str, output_path: str) -> None:
        """
        mmdc が利用できない場合の代替変換メソッド。
        
        Args:
            content (str): Mermaid内容
            output_path (str): 出力ファイルパス
        
        Raises:
            ValueError: 代替変換方法が利用できない場合
        """
        # mermaid.clisライブラリを使用した代替方法
        try:
            from mermaid.cli import convert_mermaid_to_image
            
            # 一時ファイルを作成
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp_file:
                temp_mermaid_path = temp_file.name
                temp_file.write(content)
            
            # ライブラリを使用して変換
            convert_mermaid_to_image(temp_mermaid_path, output_path)
            
            # 一時ファイルを削除
            if os.path.exists(temp_mermaid_path):
                os.remove(temp_mermaid_path)
                
            return
        except ImportError:
            pass
        
        # その他の代替方法がない場合
        # テキストファイルとして保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Mermaid Diagram (PNG conversion not available)\n\n")
            f.write("```mermaid\n")
            f.write(content)
            f.write("\n```\n")
        
        # レポート用のエラーメッセージを表示
        print("警告: Mermaid図のPNG変換ができませんでした。mmdc（Mermaid CLI）をインストールしてください。"
              "npm install -g @mermaid-js/mermaid-cli") 