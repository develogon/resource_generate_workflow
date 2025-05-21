"""
セクション構造をYAML形式で生成するモジュール。
Claude APIを使用してセクションの段落構造、学習目標、コンテンツシーケンスなどを生成する。
"""
import re
import yaml
from typing import Dict, Any, List, Optional, Union

from core.content_generator import ContentGenerator


class StructureGenerator(ContentGenerator):
    """
    セクション構造YAML生成を担当するクラス。
    ContentGeneratorを継承し、構造生成特有の処理を実装する。
    """
    
    def __init__(self, claude_service: Any, file_manager: Any, template_dir: str = "templates"):
        """
        StructureGeneratorを初期化する。
        
        Args:
            claude_service (Any): Claude APIサービス
            file_manager (Any): ファイル管理サービス
            template_dir (str, optional): テンプレートディレクトリのパス
        """
        super().__init__(claude_service, file_manager, template_dir)
    
    def generate(self, input_data: Dict[str, Any]) -> str:
        """
        セクション構造のYAMLを生成する。
        
        Args:
            input_data (dict): 生成に必要な入力データ
                - section_title: セクションタイトル
                - content: セクションの内容
                - template_path: テンプレートファイルのパス
                - images: (optional) プロンプトに含める画像データのリスト
                - chapter_title: (optional) 章タイトル
                - section_id: (optional) セクションID
                - chapter_id: (optional) 章ID
                - system_prompt: (optional) システムプロンプト
        
        Returns:
            str: 生成されたYAML構造
        """
        # 基底クラスのgenerate()メソッドを呼び出してYAMLを生成
        return super().generate(input_data)
    
    def format_output(self, raw_content: str) -> str:
        """
        生成されたYAMLコンテンツを整形する。
        
        Args:
            raw_content (str): 生成された生のYAML内容
        
        Returns:
            str: 整形されたYAML
        """
        # YAMLブロックを検出して抽出
        yaml_block_pattern = r'```yaml\n(.*?)\n```'
        yaml_match = re.search(yaml_block_pattern, raw_content, re.DOTALL)
        
        if yaml_match:
            yaml_content = yaml_match.group(1)
        else:
            # YAMLブロックが見つからない場合は、全体を処理
            yaml_content = raw_content
        
        # YAMLの構文チェック
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
            # 再度YAMLにフォーマット
            formatted_yaml = yaml.dump(parsed_yaml, sort_keys=False, allow_unicode=True)
            return formatted_yaml
        except yaml.YAMLError:
            # YAML解析に失敗した場合は元の内容をそのまま返す
            return yaml_content
    
    def validate_content(self, content: str) -> bool:
        """
        生成されたYAMLコンテンツを検証する。
        
        Args:
            content (str): 検証するYAMLコンテンツ
        
        Returns:
            bool: コンテンツが有効な場合はTrue、そうでない場合はFalse
        """
        if not content or not content.strip():
            return False
        
        # YAMLブロックを検出
        yaml_block_pattern = r'```yaml\n(.*?)\n```'
        yaml_match = re.search(yaml_block_pattern, content, re.DOTALL)
        
        if yaml_match:
            yaml_content = yaml_match.group(1)
        else:
            # YAMLブロックが見つからない場合は全体をチェック
            yaml_content = content
        
        # YAMLとして解析可能かチェック
        try:
            parsed_yaml = yaml.safe_load(yaml_content)
            
            # 必須フィールドの存在チェック
            if "paragraphs" not in parsed_yaml:
                return False
                
            # パラグラフごとに必須フィールドをチェック
            for paragraph in parsed_yaml.get("paragraphs", []):
                if "type" not in paragraph or "content_focus" not in paragraph:
                    return False
                if "content_sequence" not in paragraph:
                    return False
            
            return True
        except yaml.YAMLError:
            return False 