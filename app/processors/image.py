import os
import logging
import io
import tempfile
import subprocess
import re
import cairosvg
import hashlib
from typing import List, Dict, Any, Optional, Tuple

class ImageProcessor:
    """画像処理システム"""
    
    def __init__(self, s3_client=None):
        """初期化
        
        Args:
            s3_client: S3クライアントインスタンス（オプション）
        """
        self.logger = logging.getLogger(__name__)
        self.s3_client = s3_client
    
    def extract_images(self, content: str) -> List[Dict]:
        """コンテンツから画像を抽出
        
        Args:
            content (str): 抽出元のMarkdownコンテンツ
            
        Returns:
            List[Dict]: 抽出された画像情報のリスト
        """
        images = []
        lines = content.split("\n")
        
        for i, line in enumerate(lines):
            # Markdown画像構文の検出
            if "![" in line and "](" in line and ")" in line:
                start = line.find("![")
                end = line.find(")", start) + 1
                img_md = line[start:end]
                alt_text = img_md[2:img_md.find("]")]
                src = img_md[img_md.find("(")+1:img_md.find(")")]
                
                images.append({
                    "type": "markdown",
                    "alt_text": alt_text,
                    "src": src,
                    "line": i,
                    "full_match": img_md
                })
            # SVG構文の検出
            elif "```svg" in line:
                svg_content = []
                j = i + 1
                while j < len(lines) and "```" not in lines[j]:
                    svg_content.append(lines[j])
                    j += 1
                
                if j < len(lines):  # 閉じタグが見つかった場合
                    images.append({
                        "type": "svg",
                        "content": "\n".join(svg_content),
                        "line_start": i,
                        "line_end": j,
                        "id": f"svg_{len([img for img in images if img['type'] == 'svg']) + 1}"
                    })
            # DrawIO XML構文の検出
            elif "```drawio" in line:
                drawio_content = []
                j = i + 1
                while j < len(lines) and "```" not in lines[j]:
                    drawio_content.append(lines[j])
                    j += 1
                
                if j < len(lines):  # 閉じタグが見つかった場合
                    images.append({
                        "type": "drawio",
                        "content": "\n".join(drawio_content),
                        "line_start": i,
                        "line_end": j,
                        "id": f"drawio_{len([img for img in images if img['type'] == 'drawio']) + 1}"
                    })
            # Mermaid構文の検出
            elif "```mermaid" in line:
                mermaid_content = []
                j = i + 1
                while j < len(lines) and "```" not in lines[j]:
                    mermaid_content.append(lines[j])
                    j += 1
                
                if j < len(lines):  # 閉じタグが見つかった場合
                    images.append({
                        "type": "mermaid",
                        "content": "\n".join(mermaid_content),
                        "line_start": i,
                        "line_end": j,
                        "id": f"mermaid_{len([img for img in images if img['type'] == 'mermaid']) + 1}"
                    })
        
        self.logger.debug(f"{len(images)}個の画像を抽出しました")
        return images
    
    def process_svg(self, svg_content: str) -> bytes:
        """SVGをPNGに変換
        
        Args:
            svg_content (str): SVGコンテンツ
            
        Returns:
            bytes: 変換後のPNGデータ
        """
        try:
            # BytesIOオブジェクトを使用してメモリ内で変換
            output = io.BytesIO()
            cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), write_to=output)
            png_data = output.getvalue()
            
            self.logger.debug(f"SVGをPNGに変換しました（{len(png_data)}バイト）")
            return png_data
            
        except Exception as e:
            self.logger.error(f"SVG変換エラー: {str(e)}")
            # エラー時は1x1の透明PNGを返す
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n\xa0\xb2\x00\x00\x00\x00IEND\xaeB`\x82'
    
    def process_drawio(self, xml_content: str) -> bytes:
        """DrawIO XMLをPNGに変換
        
        Args:
            xml_content (str): DrawIO XMLコンテンツ
            
        Returns:
            bytes: 変換後のPNGデータ
        """
        try:
            # 一時ファイルにXMLを書き込み
            with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as xml_file:
                xml_file.write(xml_content.encode('utf-8'))
                xml_file_path = xml_file.name
            
            # 出力ファイルパスを設定
            output_file_path = f"{xml_file_path}.png"
            
            # DrawIO CLIを使用して変換
            # 注: この部分はDrawIO CLIのインストールと実際のコマンドラインに依存します
            command = [
                "drawio",  # DrawIOのCLIコマンド
                "--export",
                "--format", "png",
                "--output", output_file_path,
                xml_file_path
            ]
            
            # コマンド実行
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"DrawIO CLI実行エラー: {result.stderr}")
            
            # 生成されたPNGを読み込み
            with open(output_file_path, 'rb') as png_file:
                png_data = png_file.read()
            
            # 一時ファイルを削除
            os.remove(xml_file_path)
            os.remove(output_file_path)
            
            self.logger.debug(f"DrawIO XMLをPNGに変換しました（{len(png_data)}バイト）")
            return png_data
            
        except Exception as e:
            self.logger.error(f"DrawIO XML変換エラー: {str(e)}")
            # エラー時は1x1の透明PNGを返す
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n\xa0\xb2\x00\x00\x00\x00IEND\xaeB`\x82'
    
    def process_mermaid(self, mermaid_content: str) -> bytes:
        """Mermaid記法をPNGに変換
        
        Args:
            mermaid_content (str): Mermaid記法のコンテンツ
            
        Returns:
            bytes: 変換後のPNGデータ
        """
        try:
            # 一時ファイルにMermaid記法を書き込み
            with tempfile.NamedTemporaryFile(suffix='.mmd', delete=False) as mmd_file:
                mmd_file.write(mermaid_content.encode('utf-8'))
                mmd_file_path = mmd_file.name
            
            # 出力ファイルパスを設定
            output_file_path = f"{mmd_file_path}.png"
            
            # mermaid-cli (mmdc)を使用して変換
            # 注: この部分はmermaid-cliのインストールと実際のコマンドラインに依存します
            command = [
                "mmdc",  # mermaid-cliのコマンド
                "-i", mmd_file_path,
                "-o", output_file_path,
                "-b", "transparent"  # 背景を透明に
            ]
            
            # コマンド実行
            result = subprocess.run(command, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"mermaid-cli実行エラー: {result.stderr}")
            
            # 生成されたPNGを読み込み
            with open(output_file_path, 'rb') as png_file:
                png_data = png_file.read()
            
            # 一時ファイルを削除
            os.remove(mmd_file_path)
            os.remove(output_file_path)
            
            self.logger.debug(f"Mermaid記法をPNGに変換しました（{len(png_data)}バイト）")
            return png_data
            
        except Exception as e:
            self.logger.error(f"Mermaid変換エラー: {str(e)}")
            # エラー時は1x1の透明PNGを返す
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n\xa0\xb2\x00\x00\x00\x00IEND\xaeB`\x82'
    
    def upload_to_s3(self, image_data: bytes, key: str) -> str:
        """画像をS3にアップロード
        
        Args:
            image_data (bytes): アップロードする画像データ
            key (str): S3上のキー（パス）
            
        Returns:
            str: 画像の公開URL
        """
        if self.s3_client is None:
            self.logger.warning("S3クライアントが設定されていません。ダミーURLを返します。")
            return f"https://example-bucket.s3.amazonaws.com/{key}"
        
        try:
            # データをメモリ上のファイルオブジェクトに変換
            data_io = io.BytesIO(image_data)
            
            # S3にアップロード
            self.s3_client.upload_file(data=image_data, key=key, content_type="image/png")
            
            # 公開URLを取得
            public_url = self.s3_client.get_public_url(key)
            
            self.logger.debug(f"画像をS3にアップロードしました: {key}")
            return public_url
            
        except Exception as e:
            self.logger.error(f"S3アップロードエラー: {str(e)}")
            return f"https://example-bucket.s3.amazonaws.com/{key}"
    
    def replace_image_links(self, content: str, image_map: Dict[str, str]) -> str:
        """コンテンツ内の画像参照を公開URLに置換
        
        Args:
            content (str): 元のMarkdownコンテンツ
            image_map (Dict[str, str]): 置換マップ {元の参照: 公開URL}
            
        Returns:
            str: 置換後のMarkdownコンテンツ
        """
        result = content
        
        # 行ごとに処理
        lines = content.split("\n")
        modified_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Markdown画像構文の置換
            if "![" in line and "](" in line and ")" in line:
                for src, url in image_map.items():
                    if src in line:
                        # オリジナルの画像タグを取得
                        start = line.find("![")
                        end = line.find(")", start) + 1
                        img_md = line[start:end]
                        alt_text = img_md[2:img_md.find("]")]
                        
                        # 新しい画像タグを作成して置換
                        new_img_md = f"![{alt_text}]({url})"
                        line = line.replace(img_md, new_img_md)
                        
                modified_lines.append(line)
                i += 1
                
            # コードブロック（SVG、DrawIO、Mermaid）の置換
            elif any(block in line for block in ["```svg", "```drawio", "```mermaid"]):
                block_type = None
                block_id = None
                
                if "```svg" in line:
                    block_type = "svg"
                elif "```drawio" in line:
                    block_type = "drawio"
                elif "```mermaid" in line:
                    block_type = "mermaid"
                
                # ブロックの終わりを探す
                j = i + 1
                while j < len(lines) and "```" not in lines[j]:
                    j += 1
                
                if j < len(lines):  # 閉じタグが見つかった場合
                    # ブロックのIDを特定
                    content_hash = hashlib.md5("\n".join(lines[i+1:j]).encode()).hexdigest()[:8]
                    block_id = f"{block_type}_{content_hash}"
                    
                    # マップで対応するURLを探す
                    for key, url in image_map.items():
                        if key == block_id or key.startswith(f"{block_type}_"):
                            # 画像参照に置き換え
                            alt_text = f"{block_type.upper()}画像"
                            modified_lines.append(f"![{alt_text}]({url})")
                            i = j + 1  # ブロック全体をスキップ
                            break
                    else:
                        # 対応するURLが見つからない場合はそのまま追加
                        modified_lines.extend(lines[i:j+1])
                        i = j + 1
                else:
                    # 閉じタグが見つからない場合はそのまま追加
                    modified_lines.append(line)
                    i += 1
            else:
                # 通常の行はそのまま追加
                modified_lines.append(line)
                i += 1
        
        result = "\n".join(modified_lines)
        self.logger.debug(f"{len(image_map)}個の画像リンクを置換しました")
        return result 