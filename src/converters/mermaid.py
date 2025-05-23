"""Mermaid図表変換器."""

import asyncio
import subprocess
import tempfile
import os
import logging
from typing import Optional
import aiohttp

from .base import BaseConverter, ImageType
from ..config import Config

logger = logging.getLogger(__name__)


class MermaidConverter(BaseConverter):
    """Mermaid図表をPNG画像に変換する変換器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        self.mermaid_cli_path = getattr(config.image, 'mermaid_cli_path', 'mmdc')
        self.timeout = config.image.conversion_timeout
        
    def get_supported_type(self) -> ImageType:
        """サポートする画像タイプを返す."""
        return ImageType.MERMAID
        
    async def convert(self, source: str, **kwargs) -> bytes:
        """MermaidコードをPNG画像に変換.
        
        Args:
            source: Mermaidの図表コード
            **kwargs: 追加のオプション
            
        Returns:
            変換後のPNG画像データ
        """
        if not self.validate_source(source):
            raise ValueError("Invalid Mermaid source")
            
        try:
            return await self._convert_from_content(source, **kwargs)
        except Exception as e:
            logger.error(f"Mermaid conversion failed: {e}")
            raise
            
    async def _convert_from_content(self, content: str, **kwargs) -> bytes:
        """MermaidコンテンツをPNG画像に変換."""
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp_input:
            temp_input.write(content)
            temp_input_path = temp_input.name
            
        try:
            # 出力ファイルパス
            temp_output_path = temp_input_path.replace('.mmd', '.png')
            
            # Mermaid CLI実行
            if await self._check_mermaid_cli():
                result = await self._run_mermaid_cli(temp_input_path, temp_output_path, **kwargs)
            else:
                # Puppeteer経由でヘッドレス変換
                result = await self._run_mermaid_headless(content, temp_output_path, **kwargs)
                
            if not os.path.exists(temp_output_path):
                raise RuntimeError("Mermaid conversion failed - output file not created")
                
            # 変換結果を読み込み
            with open(temp_output_path, 'rb') as f:
                image_data = f.read()
                
            return image_data
            
        finally:
            # 一時ファイルを削除
            for path in [temp_input_path, temp_output_path]:
                if os.path.exists(path):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
                        
    async def _check_mermaid_cli(self) -> bool:
        """Mermaid CLIが利用可能かチェック."""
        try:
            process = await asyncio.create_subprocess_exec(
                self.mermaid_cli_path,
                '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            return process.returncode == 0
        except (FileNotFoundError, OSError):
            return False
            
    async def _run_mermaid_cli(self, input_path: str, output_path: str, **kwargs) -> bool:
        """Mermaid CLIで変換."""
        width = kwargs.get('width', self.config.image.width)
        height = kwargs.get('height', self.config.image.height)
        theme = kwargs.get('theme', 'default')
        background = kwargs.get('background', 'white')
        
        cmd = [
            self.mermaid_cli_path,
            '-i', input_path,
            '-o', output_path,
            '-w', str(width),
            '-H', str(height),
            '-t', theme,
            '-b', background
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Mermaid CLI conversion failed: {error_msg}")
                
            return True
            
        except asyncio.TimeoutError:
            logger.error("Mermaid CLI conversion timed out")
            raise
        except Exception as e:
            logger.error(f"Mermaid CLI conversion error: {e}")
            raise
            
    async def _run_mermaid_headless(self, content: str, output_path: str, **kwargs) -> bool:
        """ヘッドレスブラウザでMermaidを変換."""
        script_content = self._generate_puppeteer_script(content, output_path, **kwargs)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as script_file:
            script_file.write(script_content)
            script_path = script_file.name
            
        try:
            cmd = ['node', script_path]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Mermaid headless conversion failed: {error_msg}")
                
            return True
            
        except asyncio.TimeoutError:
            logger.error("Mermaid headless conversion timed out")
            raise
        except Exception as e:
            logger.error(f"Mermaid headless conversion error: {e}")
            raise
        finally:
            if os.path.exists(script_path):
                try:
                    os.unlink(script_path)
                except OSError:
                    pass
                    
    def _generate_puppeteer_script(self, content: str, output_path: str, **kwargs) -> str:
        """Puppeteerスクリプトを生成."""
        width = kwargs.get('width', self.config.image.width)
        height = kwargs.get('height', self.config.image.height)
        theme = kwargs.get('theme', 'default')
        background = kwargs.get('background', 'white')
        
        # Mermaidコンテンツをエスケープ
        escaped_content = content.replace('`', '\\`').replace('$', '\\$')
        
        return f"""
const puppeteer = require('puppeteer');

(async () => {{
  const browser = await puppeteer.launch({{
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  }});
  
  try {{
    const page = await browser.newPage();
    await page.setViewport({{ width: {width}, height: {height} }});
    
    // MermaidのCDNを読み込んでページを作成
    const html = `
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 20px;
                background-color: {background};
                font-family: 'Arial', sans-serif;
            }}
            .mermaid {{
                max-width: 100%;
                margin: 0 auto;
            }}
        </style>
    </head>
    <body>
        <div class="mermaid">
{escaped_content}
        </div>
        <script>
            mermaid.initialize({{
                theme: '{theme}',
                startOnLoad: true,
                fontFamily: 'Arial, sans-serif'
            }});
        </script>
    </body>
    </html>
    `;
    
    await page.setContent(html);
    
    // Mermaidのレンダリング完了を待機
    await page.waitForSelector('.mermaid svg', {{ timeout: 10000 }});
    await page.waitForTimeout(1000);
    
    // 要素のスクリーンショットを取得
    const element = await page.$('.mermaid');
    await element.screenshot({{
      path: '{output_path}',
      type: 'png',
      omitBackground: {str(background == 'transparent').lower()}
    }});
    
  }} catch (error) {{
    console.error('Mermaid conversion error:', error);
    process.exit(1);
  }} finally {{
    await browser.close();
  }}
}})();
"""
        
    def validate_source(self, source: str) -> bool:
        """Mermaidソースの検証."""
        if not source or not isinstance(source, str):
            return False
            
        # Mermaidの基本的なキーワードをチェック
        mermaid_keywords = [
            'graph', 'flowchart', 'sequenceDiagram', 'classDiagram',
            'stateDiagram', 'erDiagram', 'gantt', 'pie', 'journey',
            'gitgraph', 'requirementDiagram', 'timeline'
        ]
        
        content_lower = source.lower().strip()
        
        # 先頭にMermaidキーワードがあるかチェック
        for keyword in mermaid_keywords:
            if content_lower.startswith(keyword.lower()):
                return True
                
        # コードブロック内のMermaidもチェック
        if 'mermaid' in content_lower and any(keyword in content_lower for keyword in mermaid_keywords):
            return True
            
        return False
        
    def extract_mermaid_content(self, source: str) -> str:
        """MarkdownコードブロックからMermaidコンテンツを抽出."""
        lines = source.strip().split('\n')
        
        # コードブロックの開始・終了を検出
        in_mermaid_block = False
        mermaid_lines = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('```mermaid'):
                in_mermaid_block = True
                continue
            elif line.startswith('```') and in_mermaid_block:
                in_mermaid_block = False
                break
            elif in_mermaid_block:
                mermaid_lines.append(line)
                
        if mermaid_lines:
            return '\n'.join(mermaid_lines)
        
        # コードブロックがない場合はそのまま返す
        return source 