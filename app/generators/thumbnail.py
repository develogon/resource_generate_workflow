import os
import re
import yaml
import logging
import asyncio
from typing import Dict, Any, Optional, Union, Tuple, List

from app.generators.base import BaseGenerator
from app.clients.openai import OpenAIClient
from app.clients.s3 import S3Client


class ThumbnailGenerator(BaseGenerator):
    """サムネイルジェネレータ

    AIを活用してサムネイル画像を生成するジェネレータクラス
    """

    def __init__(self, openai_api_key=None, s3_client=None):
        """初期化

        Args:
            openai_api_key (str, optional): OpenAI API キー. デフォルトはNone (環境変数から取得)
            s3_client (S3Client, optional): S3クライアントインスタンス. デフォルトはNone (新規作成)
        """
        super().__init__()
        self.openai_client = OpenAIClient(openai_api_key) if openai_api_key else OpenAIClient()
        self.s3_client = s3_client if s3_client else S3Client()

    def load_template(self, template_path: Optional[str] = None) -> Dict:
        """テンプレート設定を読み込む

        Args:
            template_path (str, optional): テンプレート設定ファイルのパス. デフォルトはNone

        Returns:
            Dict: テンプレート設定
        """
        default_template = {
            "size": "1024x1024",
            "style": "digital art",
            "quality": "high",
            "background": "simple, clean, professional"
        }
        
        if not template_path:
            return default_template
            
        try:
            # テンプレートファイルを読み込む
            with open(template_path, 'r', encoding='utf-8') as f:
                template = yaml.safe_load(f)
                
            # 必須キーが存在することを確認
            for key in ['size', 'style', 'quality', 'background']:
                if key not in template:
                    template[key] = default_template[key]
                    
            return template
            
        except (FileNotFoundError, yaml.YAMLError) as e:
            self.logger.error(f"テンプレート読み込みエラー: {str(e)}")
            return default_template

    def prepare_prompt(self, title: str, description: str, template: Dict, **kwargs) -> str:
        """サムネイル生成用プロンプトを準備する

        Args:
            title (str): 記事タイトル
            description (str): 記事の説明文
            template (Dict): テンプレート設定
            **kwargs: 追加オプション

        Returns:
            str: 準備されたプロンプト
        """
        # タイトルから不要な記号を削除
        clean_title = re.sub(r'[【】「」『』（）()]', '', title)
        
        # キーワードがあれば追加
        keywords = kwargs.get('keywords', [])
        keywords_text = ", ".join(keywords) if keywords else "minimal, professional"
        
        # システムプロンプト（役割設定）を取得
        system_prompt = self.get_system_prompt('thumbnail')
        
        # メッセージプロンプト（具体的な指示）を取得し、変数を置換
        message_prompt = self.get_message_prompt('thumbnail')
        message_prompt = message_prompt.replace('{{TITLE}}', clean_title)
        message_prompt = message_prompt.replace('{{DESCRIPTION}}', description[:100] + '...')
        message_prompt = message_prompt.replace('{{STYLE}}', template.get('style', 'digital art'))
        message_prompt = message_prompt.replace('{{BACKGROUND}}', template.get('background', 'simple, clean, professional'))
        message_prompt = message_prompt.replace('{{KEYWORDS}}', keywords_text)
        
        # システムプロンプトとメッセージプロンプトを組み合わせる
        combined_prompt = f"""
# サムネイル生成

## システムプロンプト
{system_prompt}

## メッセージプロンプト
{message_prompt}
"""
        return combined_prompt

    def process_response(self, response: bytes) -> bytes:
        """API応答を処理する

        Args:
            response (bytes): 画像データ

        Returns:
            bytes: 処理された画像データ
            
        Raises:
            ValueError: 画像データが空の場合
        """
        # 画像データが空でないことを確認
        if not response or len(response) == 0:
            self.logger.error("API応答から画像データを取得できませんでした")
            raise ValueError("API応答から画像データを取得できませんでした")
            
        # この実装では特に処理は行わず、そのまま返す
        # 将来的には画像処理（リサイズ、フィルタ適用など）を追加する可能性がある
        return response

    async def generate(self, title: str, description: str, output_path: Optional[str] = None, 
                     upload_to_s3: bool = False, s3_key: Optional[str] = None,
                     template_path: Optional[str] = None, **kwargs) -> Tuple[bytes, Optional[str]]:
        """サムネイル画像を生成する

        Args:
            title (str): 記事タイトル
            description (str): 記事の説明文
            output_path (str, optional): 出力先ファイルパス. デフォルトはNone
            upload_to_s3 (bool, optional): S3にアップロードするかどうか. デフォルトはFalse
            s3_key (str, optional): S3のキー. デフォルトはNone
            template_path (str, optional): テンプレートファイルパス. デフォルトはNone
            **kwargs: 追加オプション

        Returns:
            Tuple[bytes, Optional[str]]: 生成された画像データとS3 URL（アップロードした場合）
        """
        # テンプレートを読み込む
        template = self.load_template(template_path)
        
        # プロンプトを準備
        prompt = self.prepare_prompt(title, description, template, **kwargs)
        
        # サイズを取得
        size = template.get('size', '1024x1024')
        
        # 品質を取得
        quality = template.get('quality', 'standard')
        
        # 画像を生成
        image_data = await self.openai_client.generate_image(prompt, size, quality)
        
        # 応答を処理
        processed_image = self.process_response(image_data)
        
        # 出力先が指定されていれば保存
        if output_path:
            # from app.utils.file import FileUtils
            # FileUtils.write_binary_file(output_path, processed_image)
            pass
            
        # S3にアップロードする場合
        s3_url = None
        if upload_to_s3 and self.s3_client:
            if not s3_key:
                # キーが指定されていない場合はタイトルからキーを生成
                clean_title = re.sub(r'[^\w\-]', '_', title.lower())
                s3_key = f"thumbnails/{clean_title}_{int(asyncio.get_event_loop().time())}.png"
                
            # S3にアップロード
            s3_url = self.s3_client.upload_file(data=processed_image, key=s3_key, content_type="image/png")
            
        return processed_image, s3_url

    def generate_thumbnail(self, title: str, description: str, output_path: Optional[str] = None, 
                         upload_to_s3: bool = False, s3_key: Optional[str] = None,
                         template_path: Optional[str] = None, **kwargs) -> Tuple[bytes, Optional[str]]:
        """サムネイル画像を生成する（同期版）

        Args:
            title (str): 記事タイトル
            description (str): 記事の説明文
            output_path (str, optional): 出力先ファイルパス. デフォルトはNone
            upload_to_s3 (bool, optional): S3にアップロードするかどうか. デフォルトはFalse
            s3_key (str, optional): S3のキー. デフォルトはNone
            template_path (str, optional): テンプレートファイルパス. デフォルトはNone
            **kwargs: 追加オプション

        Returns:
            Tuple[bytes, Optional[str]]: 生成された画像データとS3 URL（アップロードした場合）
        """
        try:
            # 現在のイベントループを取得
            loop = asyncio.get_event_loop()
            
            # イベントループの状態に関わらず非同期メソッドを実行
            return loop.run_until_complete(
                self.generate(title, description, output_path, upload_to_s3, s3_key, template_path, **kwargs)
            )
        except RuntimeError:
            # イベントループがない場合、新しく作成して実行
            return asyncio.run(
                self.generate(title, description, output_path, upload_to_s3, s3_key, template_path, **kwargs)
            ) 