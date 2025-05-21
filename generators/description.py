"""
概要生成を担当するモジュール。
Claude APIを使用してタイトル構造から概要を生成する。
標準的なフォーマットのテンプレートも追記する。
"""
import re
from typing import Dict, Any, Optional


from core.content_generator import ContentGenerator


class DescriptionGenerator(ContentGenerator):
    """
    概要生成を担当するクラス。
    ContentGeneratorを継承し、概要生成に特化した処理を実装する。
    """
    
    def __init__(self, claude_service: Any, file_manager: Any, template_dir: str = "templates"):
        """
        DescriptionGeneratorを初期化する。
        
        Args:
            claude_service (Any): Claude APIサービス
            file_manager (Any): ファイル管理サービス
            template_dir (str, optional): テンプレートディレクトリのパス
        """
        super().__init__(claude_service, file_manager, template_dir)
        self.description_template_path = f"{template_dir}/description_template.md"
    
    def generate(self, input_data: Dict[str, Any]) -> str:
        """
        概要を生成する。
        
        Args:
            input_data (dict): 生成に必要な入力データ
                - title: タイトル
                - structure_path: 文書構造ファイルのパス
                - template_path: テンプレートファイルのパス
                - language (optional): 対象言語
                - description_template_path (optional): 追記用テンプレートパス
        
        Returns:
            str: 生成された概要
        """
        # 文書構造ファイルの読み込み
        structure_path = input_data.get("structure_path")
        structure_content = self.file_manager.read_content(structure_path)
        
        # 構造データを入力データに追加
        input_data["structure"] = structure_content
        
        # 概要テンプレートパスを取得（指定がなければデフォルト）
        description_template_path = input_data.get("description_template_path", self.description_template_path)
        
        # 親クラスのgenerateメソッドを呼び出す
        generated_description = super().generate(input_data)
        
        # 概要テンプレートの追記（存在する場合）
        try:
            template_content = self.file_manager.read_content(description_template_path)
            generated_description = self.append_template(
                generated_description, 
                template_content, 
                input_data
            )
        except Exception as e:
            print(f"テンプレート追記エラー: {str(e)}")
        
        return generated_description
    
    def format_output(self, raw_content: str) -> str:
        """
        生成された概要コンテンツを整形する。
        
        Args:
            raw_content (str): 生成された生の概要コンテンツ
        
        Returns:
            str: 整形された概要
        """
        # 余分な空行を圧縮
        content = re.sub(r'\n{3,}', '\n\n', raw_content.strip())
        
        # 見出しの前後に空行を確保
        content = re.sub(r'([^\n])\n(#+\s)', r'\1\n\n\2', content)
        content = re.sub(r'(#+\s.*?)\n([^#\n])', r'\1\n\n\2', content)
        
        return content
    
    def validate_content(self, content: str) -> bool:
        """
        生成された概要コンテンツを検証する。
        
        Args:
            content (str): 検証する概要コンテンツ
        
        Returns:
            bool: コンテンツが有効な場合はTrue、そうでない場合はFalse
        """
        if not content or not content.strip():
            return False
        
        # 概要には最低限タイトルと少なくとも1つのセクションが含まれているべき
        has_title = bool(re.search(r'^#\s+.+', content, re.MULTILINE))
        has_section = bool(re.search(r'^##\s+.+', content, re.MULTILINE))
        
        return has_title and has_section
    
    def append_template(self, description: str, template: str, context: Dict[str, Any]) -> str:
        """
        概要にテンプレートを追記する。
        
        Args:
            description (str): 元の概要コンテンツ
            template (str): 追記するテンプレート
            context (dict): テンプレート変数の辞書
        
        Returns:
            str: テンプレートが追記された概要
        """
        if not template:
            return description
        
        # テンプレート変数の置換
        formatted_template = self.optimize_prompt(template, context)
        
        # 概要とテンプレートの結合
        combined = description.rstrip() + "\n\n" + formatted_template.lstrip()
        
        return combined 