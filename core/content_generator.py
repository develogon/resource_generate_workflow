"""
様々なコンテンツ生成を抽象化した基底クラスを提供するモジュール。
Factory Method パターンを使用して、各種コンテンツ生成器の共通機能を定義する。
"""
import os
import re
import string
from typing import Dict, List, Any, Optional, Union


class ContentGenerator:
    """
    コンテンツ生成を担当する基底クラス。
    Factory Method パターンを使用して、各種コンテンツ生成器の共通機能を定義する。
    
    派生クラスは以下のメソッドをオーバーライドすることを想定:
    - format_output: 生成されたコンテンツの整形
    - validate_content: 生成されたコンテンツの検証
    """

    def __init__(
        self, 
        claude_service: Any, 
        file_manager: Any, 
        template_dir: str = "templates"
    ):
        """
        ContentGeneratorを初期化する

        Args:
            claude_service (Any): Claude APIサービス
            file_manager (Any): ファイル管理サービス
            template_dir (str, optional): テンプレートディレクトリのパス
        """
        self.claude_service = claude_service
        self.file_manager = file_manager
        self.template_dir = template_dir

    def generate(self, input_data: Dict[str, Any]) -> str:
        """
        コンテンツを生成する (Factory Methodの中心となるメソッド)

        Args:
            input_data (dict): 生成に必要な入力データ
                - template_path: テンプレートファイルのパス
                - context: テンプレート変数の辞書
                - images: (optional) プロンプトに含める画像データのリスト

        Returns:
            str: 生成されたコンテンツ
        """
        # テンプレートの読み込み
        template_path = input_data.get("template_path")
        context = input_data.get("context", {})
        
        try:
            # テンプレートの読み込み
            template_content = self.file_manager.read_content(template_path)
            
            # プロンプトの最適化
            prompt = self.optimize_prompt(template_content, context)
            
            # 画像データの取得
            images = input_data.get("images", [])
            
            # Claude APIでコンテンツ生成
            response = self.claude_service.generate_content(prompt, images)
            
            # 生成されたコンテンツを取得
            raw_content = response.get("content", "")
            
            # 生成コンテンツの検証
            if not self.validate_content(raw_content):
                raise ValueError("生成されたコンテンツが無効です")
            
            # 生成コンテンツのフォーマット
            formatted_content = self.format_output(raw_content)
            
            return formatted_content
            
        except Exception as e:
            # エラーログ出力
            print(f"コンテンツ生成エラー: {str(e)}")
            raise

    def format_output(self, raw_content: str) -> str:
        """
        生成されたコンテンツをフォーマットする
        派生クラスでオーバーライドすることを想定

        Args:
            raw_content (str): 生成された生のコンテンツ

        Returns:
            str: フォーマットされたコンテンツ
        """
        # 基底クラスではそのまま返す
        return raw_content

    def validate_content(self, content: str) -> bool:
        """
        生成されたコンテンツを検証する
        派生クラスでオーバーライドすることを想定

        Args:
            content (str): 検証するコンテンツ

        Returns:
            bool: コンテンツが有効な場合はTrue、そうでない場合はFalse
        """
        # 基底クラスでは最低限の検証のみ実行
        if content is None or content.strip() == "":
            return False
        return True

    def optimize_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """
        テンプレートと変数を使ってプロンプトを最適化する

        Args:
            template (str): プロンプトのテンプレート
            context (dict): テンプレート変数の辞書

        Returns:
            str: 最適化されたプロンプト
        """
        # シンプルなテンプレート変数置換 ({{variable}} 形式)
        result = template
        
        # テンプレート変数の置換
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            if isinstance(value, str):
                result = result.replace(placeholder, value)
            elif value is not None:
                result = result.replace(placeholder, str(value))
            else:
                # 値がNoneの場合は空文字に置換
                result = result.replace(placeholder, "")
        
        return result

    @classmethod
    def create(cls, generator_type: str, **services):
        """
        ジェネレータタイプに応じたContentGeneratorのサブクラスのインスタンスを作成する
        Factory Methodパターンの実装

        Args:
            generator_type (str): 生成器タイプ ("article", "script", "json_script", "tweets", etc.)
            **services: 必要なサービスのキーワード引数

        Returns:
            ContentGenerator: 生成されたContentGeneratorのサブクラスのインスタンス

        Raises:
            ValueError: 不明な生成器タイプの場合
        """
        # インポートは関数内で行い、循環参照を防ぐ
        if generator_type == "article":
            from generators.article import ArticleGenerator
            return ArticleGenerator(**services)
        elif generator_type == "script":
            from generators.script import ScriptGenerator
            return ScriptGenerator(**services)
        elif generator_type == "json_script":
            from generators.json_script import JsonScriptGenerator
            return JsonScriptGenerator(**services)
        elif generator_type == "tweets":
            from generators.tweets import TweetsGenerator
            return TweetsGenerator(**services)
        elif generator_type == "description":
            from generators.description import DescriptionGenerator
            return DescriptionGenerator(**services)
        else:
            raise ValueError(f"不明な生成器タイプです: {generator_type}") 