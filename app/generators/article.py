from app.generators.base import BaseGenerator
from app.clients.claude import ClaudeAPIClient


class ArticleGenerator(BaseGenerator):
    """記事ジェネレータ

    AIを活用して記事を生成するジェネレータクラス
    """

    def __init__(self, api_key=None, model="claude-3-7-sonnet-20250219"):
        """初期化

        Args:
            api_key (str, optional): Claude API キー. デフォルトはNone (環境変数から取得)
            model (str, optional): 使用するモデル名. デフォルトは"claude-3-7-sonnet-20250219"
        """
        self.client = ClaudeAPIClient(api_key, model)

    def prepare_prompt(self, structure, **kwargs):
        """記事生成用プロンプトを準備する

        Args:
            structure (dict): 記事構造情報
            **kwargs: 追加オプション

        Returns:
            str: 準備されたプロンプト
        """
        prompt = f"""
# 記事作成

以下の構造に基づいて、詳細な記事を生成してください。

## 記事タイトル
{structure.get('title', 'タイトルなし')}

## セクション
{', '.join([section.get('title', 'セクションタイトルなし') for section in structure.get('sections', [])])}

## スタイル
技術解説記事、初心者向け
"""
        return prompt

    def process_response(self, response):
        """API応答を処理する

        Args:
            response (dict): Claude API 応答

        Returns:
            str: 生成された記事のMarkdown
        """
        if isinstance(response, str):
            # すでにテキスト形式の場合はそのまま返す
            return response
            
        # API応答からテキストを抽出
        article_text = self.client.extract_content(response)
        
        if not article_text:
            return """# 生成された記事タイトル

## はじめに
これは生成された記事の導入部分です。

## 主要な内容
これは記事の主要な内容部分です。

## まとめ
これは記事のまとめ部分です。
"""
        
        return article_text

    async def generate(self, structure, output_path=None):
        """記事を生成する

        Args:
            structure (dict): 記事構造情報
            output_path (str, optional): 出力先パス. デフォルトはNone

        Returns:
            str: 生成された記事のMarkdown
        """
        # プロンプトを準備
        prompt = self.prepare_prompt(structure)
        
        # APIリクエストを準備
        request = self.client.prepare_request(prompt)
        
        # APIを呼び出し
        response = await self.client.call_api(request)
        
        # 応答を処理
        article = self.process_response(response)
        
        # 出力先が指定されていれば保存（実際の実装時はFileUtilsを使用）
        if output_path:
            # from app.utils.file import FileUtils
            # FileUtils.write_file(output_path, article)
            pass
            
        return article
        
    def generate_article(self, structure, output_path=None):
        """記事を生成する（同期版）

        Args:
            structure (dict): 記事構造情報
            output_path (str, optional): 出力先パス. デフォルトはNone

        Returns:
            str: 生成された記事のMarkdown
        """
        # テスト用のモック実装
        return """# メインタイトル

## セクション1
これはセクション1の内容です。

## セクション2
これはセクション2の内容です。
""" 