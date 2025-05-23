"""DrawIO図表変換器."""

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


class DrawIOConverter(BaseConverter):
    """DrawIO図表をPNG画像に変換する変換器."""
    
    def __init__(self, config: Config):
        """初期化."""
        super().__init__(config)
        self.drawio_path = config.image.drawio_path
        self.timeout = config.image.conversion_timeout
        
    def get_supported_type(self) -> ImageType:
        """サポートする画像タイプを返す."""
        return ImageType.DRAWIO
        
    async def convert(self, source: str, **kwargs) -> bytes:
        """DrawIOファイルをPNG画像に変換.
        
        Args:
            source: DrawIOファイルのコンテンツまたはURL
            **kwargs: 追加のオプション
            
        Returns:
            変換後のPNG画像データ
        """
        if not self.validate_source(source):
            raise ValueError("Invalid DrawIO source")
            
        try:
            # ソースがURLかコンテンツかを判定
            if source.startswith(('http://', 'https://')):
                return await self._convert_from_url(source, **kwargs)
            else:
                return await self._convert_from_content(source, **kwargs)
                
        except Exception as e:
            logger.error(f"DrawIO conversion failed: {e}")
            raise
            
    async def _convert_from_url(self, url: str, **kwargs) -> bytes:
        """URLからDrawIOファイルをダウンロードして変換."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to download DrawIO file from {url}")
                    
                content = await response.text()
                return await self._convert_from_content(content, **kwargs)
                
    async def _convert_from_content(self, content: str, **kwargs) -> bytes:
        """DrawIOコンテンツをPNG画像に変換."""
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.drawio', delete=False) as temp_input:
            temp_input.write(content)
            temp_input_path = temp_input.name
            
        try:
            # 出力ファイルパス
            temp_output_path = temp_input_path.replace('.drawio', '.png')
            
            # DrawIOコマンドライン実行
            if self.drawio_path and os.path.exists(self.drawio_path):
                # ローカルのdraw.ioアプリを使用
                result = await self._run_drawio_desktop(temp_input_path, temp_output_path, **kwargs)
            else:
                # Puppeteer経由でヘッドレス変換
                result = await self._run_drawio_headless(temp_input_path, temp_output_path, **kwargs)
                
            if not os.path.exists(temp_output_path):
                raise RuntimeError("DrawIO conversion failed - output file not created")
                
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
                        
    async def _run_drawio_desktop(self, input_path: str, output_path: str, **kwargs) -> bool:
        """デスクトップ版draw.ioで変換."""
        width = kwargs.get('width', self.config.image.width)
        height = kwargs.get('height', self.config.image.height)
        
        cmd = [
            self.drawio_path,
            '--export',
            '--format', 'png',
            '--width', str(width),
            '--height', str(height),
            '--output', output_path,
            input_path
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
                raise RuntimeError(f"DrawIO conversion failed: {error_msg}")
                
            return True
            
        except asyncio.TimeoutError:
            logger.error("DrawIO conversion timed out")
            raise
        except Exception as e:
            logger.error(f"DrawIO desktop conversion error: {e}")
            raise
            
    async def _run_drawio_headless(self, input_path: str, output_path: str, **kwargs) -> bool:
        """ヘッドレスブラウザでDrawIOを変換."""
        # Puppeteerスクリプトを実行
        script_content = self._generate_puppeteer_script(input_path, output_path, **kwargs)
        
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
                raise RuntimeError(f"DrawIO headless conversion failed: {error_msg}")
                
            return True
            
        except asyncio.TimeoutError:
            logger.error("DrawIO headless conversion timed out")
            raise
        except Exception as e:
            logger.error(f"DrawIO headless conversion error: {e}")
            raise
        finally:
            if os.path.exists(script_path):
                try:
                    os.unlink(script_path)
                except OSError:
                    pass
                    
    def _generate_puppeteer_script(self, input_path: str, output_path: str, **kwargs) -> str:
        """Puppeteerスクリプトを生成."""
        width = kwargs.get('width', self.config.image.width)
        height = kwargs.get('height', self.config.image.height)
        
        return f"""
const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {{
  const browser = await puppeteer.launch({{
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  }});
  
  try {{
    const page = await browser.newPage();
    await page.setViewport({{ width: {width}, height: {height} }});
    
    // DrawIOファイルを読み込み
    const drawioContent = fs.readFileSync('{input_path}', 'utf8');
    
    // draw.ioエディターを開く
    await page.goto('https://app.diagrams.net/?embed=1&proto=json', {{
      waitUntil: 'networkidle0'
    }});
    
    // ファイルをロード
    await page.evaluate((content) => {{
      window.postMessage({{
        action: 'load',
        xml: content
      }}, '*');
    }}, drawioContent);
    
    // レンダリング完了を待機
    await page.waitForTimeout(2000);
    
    // SVGを取得してPNGに変換
    const element = await page.$('.geDiagramContainer');
    await element.screenshot({{
      path: '{output_path}',
      type: 'png'
    }});
    
  }} finally {{
    await browser.close();
  }}
}})();
"""
        
    def validate_source(self, source: str) -> bool:
        """DrawIOソースの検証."""
        if not source:
            return False
            
        # URLの場合
        if source.startswith(('http://', 'https://')):
            return True
            
        # XMLコンテンツの場合（簡易チェック）
        if '<mxfile' in source or '<diagram' in source:
            return True
            
        return False 