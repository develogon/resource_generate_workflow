import csv
import io
import logging
import asyncio
import os
from typing import Dict, Any, Optional, Union, List

from app.generators.base import BaseGenerator
from app.clients.claude import ClaudeAPIClient


class TweetGenerator(BaseGenerator):
    """ツイートジェネレータ

    AIを活用してツイート（短文投稿）を生成するジェネレータクラス
    """

    def __init__(self, api_key=None, model="claude-3-7-sonnet-20250219"):
        """初期化

        Args:
            api_key (str, optional): Claude API キー. デフォルトはNone (環境変数から取得)
            model (str, optional): 使用するモデル名. デフォルトは"claude-3-7-sonnet-20250219"
        """
        super().__init__()
        self.client = ClaudeAPIClient(api_key, model)
        self.logger = logging.getLogger(__name__)

    def prepare_prompt(self, structure: Dict, article_content: str, **kwargs) -> str:
        """ツイート生成用プロンプトを準備する

        Args:
            structure (Dict): コンテンツ構造情報
            article_content (str): 記事内容
            **kwargs: 追加オプション

        Returns:
            str: 準備されたプロンプト
        """
        # オプションパラメータの取得
        tweet_count = kwargs.get('tweet_count', 5)
        max_length = kwargs.get('max_length', 280)
        
        # システムプロンプト（役割設定）を取得
        system_prompt = self.get_system_prompt('tweet')
        
        # メッセージプロンプト（具体的な指示）を取得し、変数を置換
        message_prompt = self.get_message_prompt('tweet')
        message_prompt = message_prompt.replace('{{ARTICLE_CONTENT}}', article_content[:500] + '... （長いため省略）')
        message_prompt = message_prompt.replace('{{TWEET_COUNT}}', str(tweet_count))
        message_prompt = message_prompt.replace('{{MAX_LENGTH}}', str(max_length))
        
        # システムプロンプトとメッセージプロンプトを組み合わせる
        combined_prompt = f"""
# ツイート生成

## システムプロンプト
{system_prompt}

## メッセージプロンプト
{message_prompt}

## 記事タイトル
{structure.get('title', 'タイトルなし')}
"""
        return combined_prompt

    def process_response(self, response: Union[Dict, str]) -> str:
        """API応答を処理する

        Args:
            response (Dict or str): Claude API 応答

        Returns:
            str: 生成されたツイートのCSV
            
        Raises:
            ValueError: コンテンツが空の場合やCSV形式が抽出できない場合
        """
        if isinstance(response, str):
            # すでにテキスト形式の場合はそのまま返す
            return response
            
        # API応答からテキストを抽出
        content = self.client.extract_content(response)
        
        if not content:
            self.logger.error("APIレスポンスからコンテンツを抽出できませんでした")
            raise ValueError("APIレスポンスからコンテンツを抽出できませんでした")
        
        # CSV形式を抽出
        csv_content = ""
        in_csv_block = False
        
        for line in content.split('\n'):
            if line.strip() == "```csv":
                in_csv_block = True
                continue
            elif line.strip() == "```" and in_csv_block:
                in_csv_block = False
                continue
                
            if in_csv_block:
                csv_content += line + "\n"
                
        # CSV形式が抽出できなかった場合はエラーを返す
        if not csv_content:
            self.logger.error("レスポンスからCSV形式を抽出できませんでした")
            raise ValueError("レスポンスからCSV形式を抽出できませんでした")
                
        return csv_content

    def parse_csv_to_tweets(self, csv_content: str) -> List[Dict]:
        """CSVコンテンツをツイートリストに変換する

        Args:
            csv_content (str): CSV形式のツイートデータ

        Returns:
            List[Dict]: ツイート情報のリスト
        """
        tweets = []
        
        try:
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            
            for row in reader:
                tweets.append({
                    'text': row.get('tweet_text', ''),
                    'hashtags': row.get('hashtags', '').split(),
                    'media_suggestion': row.get('media_suggestion', '')
                })
                
        except Exception as e:
            self.logger.error(f"CSV解析エラー: {e}")
            
        return tweets

    async def generate(self, structure: Dict, article_content: str, tweet_count: int = 5, 
                      max_length: int = 280, output_path: Optional[str] = None) -> str:
        """ツイートを生成する

        Args:
            structure (Dict): コンテンツ構造情報
            article_content (str): 記事内容
            tweet_count (int, optional): 生成するツイート数. デフォルトは5
            max_length (int, optional): ツイートの最大文字数. デフォルトは280
            output_path (str, optional): 出力先パス. デフォルトはNone
                                         Noneの場合はget_output_path()で自動生成

        Returns:
            str: 生成されたツイートのCSV
        """
        # 出力パスが指定されていない場合は自動生成
        if output_path is None:
            # structureからlevelを判断
            if 'section_name' in structure:
                level = 'section'
            elif 'chapter_name' in structure:
                level = 'chapter'
            else:
                level = 'title'
            
            output_path = self.get_output_path(structure, level, 'tweets.csv')
        
        # プロンプトを準備
        prompt = self.prepare_prompt(
            structure, 
            article_content, 
            tweet_count=tweet_count,
            max_length=max_length
        )
        
        # APIリクエストを準備
        request = self.client.prepare_request(prompt)
        
        # APIを呼び出し（同期関数なのでawaitは使わない）
        response = self.client.call_api(request)
        
        # 応答を処理
        csv_content = self.process_response(response)
        
        # 出力先が指定されていれば保存（実際の実装時はFileUtilsを使用）
        if output_path:
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            pass
            
        return csv_content
        
    def generate_tweets(self, structure: Dict, article_content: str, tweet_count: int = 5,
                        max_length: int = 280, output_path: Optional[str] = None) -> str:
        """ツイートを生成する（同期版）

        Args:
            structure (Dict): コンテンツ構造情報
            article_content (str): 記事内容
            tweet_count (int, optional): 生成するツイート数. デフォルトは5
            max_length (int, optional): ツイートの最大文字数. デフォルトは280
            output_path (str, optional): 出力先パス. デフォルトはNone
                                         Noneの場合はget_output_path()で自動生成

        Returns:
            str: 生成されたツイートのCSV
        """
        try:
            # 現在のイベントループを取得
            loop = asyncio.get_event_loop()
            
            # イベントループの状態に関わらず非同期メソッドを実行
            return loop.run_until_complete(
                self.generate(structure, article_content, tweet_count, max_length, output_path)
            )
        except RuntimeError:
            # イベントループがない場合、新しく作成して実行
            return asyncio.run(
                self.generate(structure, article_content, tweet_count, max_length, output_path)
            ) 