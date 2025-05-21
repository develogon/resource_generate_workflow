"""
台本JSONの生成を担当するモジュール。
Claude APIを使用してJSON形式の台本データを生成・検証する。
"""
import re
import json
import datetime
from typing import Dict, Any, List, Optional, Union


from core.content_generator import ContentGenerator


class JSONScriptGenerator(ContentGenerator):
    """
    台本JSON生成を担当するクラス。
    ContentGeneratorを継承し、JSON形式の台本生成に特化した処理を実装する。
    """
    
    def __init__(self, claude_service: Any, file_manager: Any, template_dir: str = "templates"):
        """
        JSONScriptGeneratorを初期化する。
        
        Args:
            claude_service (Any): Claude APIサービス
            file_manager (Any): ファイル管理サービス
            template_dir (str, optional): テンプレートディレクトリのパス
        """
        super().__init__(claude_service, file_manager, template_dir)
        self.required_fields = ["title", "scenes"]
    
    def generate(self, input_data: Dict[str, Any]) -> str:
        """
        台本JSONを生成する。
        
        Args:
            input_data (dict): 生成に必要な入力データ
                - ARTICLE_CONTENT: 元の記事コンテンツ
                - template_path: テンプレートファイルのパス
                - section_title (optional): セクションタイトル
                - language (optional): 対象言語
        
        Returns:
            str: 生成された台本JSON
        """
        # セクションタイトルをAARTICLE_CONTENTから抽出（存在する場合）
        if "section_title" not in input_data and "ARTICLE_CONTENT" in input_data:
            article_content = input_data.get("ARTICLE_CONTENT", "")
            title_match = re.search(r'^#\s+(.+)$', article_content, re.MULTILINE)
            if title_match:
                input_data["section_title"] = title_match.group(1)
        
        # 言語を抽出（存在する場合）
        if "language" not in input_data and "ARTICLE_CONTENT" in input_data:
            article_content = input_data.get("ARTICLE_CONTENT", "")
            lang_match = re.search(r'言語[:：]\s*(\w+)', article_content)
            if lang_match:
                input_data["language"] = lang_match.group(1)
        
        # 親クラスのgenerateメソッドを呼び出す
        return super().generate(input_data)
    
    def format_output(self, raw_content: str) -> str:
        """
        生成されたJSONコンテンツを整形する。
        
        Args:
            raw_content (str): 生成された生のJSONコンテンツ
        
        Returns:
            str: 整形されたJSONコンテンツ
        
        Raises:
            ValueError: JSONのパースに失敗した場合
        """
        # JSONコンテンツを抽出
        try:
            json_content = self.extract_json(raw_content)
        except ValueError as e:
            raise ValueError(f"JSONコンテンツの抽出に失敗しました: {str(e)}")
        
        # JSONデータをパース
        try:
            script_data = json.loads(json_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSONの解析に失敗しました: {str(e)}")
        
        # デフォルトの継続時間を設定（存在しない場合）
        if "duration" not in script_data:
            script_data["duration"] = "00:05:00"
        
        # 継続時間の調整
        script_data = self.modify_durations(script_data)
        
        # 整形されたJSONを返す
        return json.dumps(script_data, indent=2, ensure_ascii=False)
    
    def validate_content(self, content: str) -> bool:
        """
        生成されたJSONコンテンツを検証する。
        
        Args:
            content (str): 検証するJSONコンテンツ
        
        Returns:
            bool: コンテンツが有効な場合はTrue、そうでない場合はFalse
        """
        if not content or not content.strip():
            return False
        
        # JSONデータの解析と検証
        try:
            # JSONコンテンツを抽出
            json_content = self.extract_json(content)
            script_data = json.loads(json_content)
            
            # 必須フィールドの確認
            for field in self.required_fields:
                if field not in script_data:
                    return False
            
            # scenesが配列であることを確認
            if not isinstance(script_data["scenes"], list) or len(script_data["scenes"]) == 0:
                return False
            
            return True
            
        except (ValueError, json.JSONDecodeError):
            return False
    
    def extract_json(self, content: str) -> str:
        """
        テキストからJSONブロックを抽出する。
        
        Args:
            content (str): JSONブロックを含むテキスト
        
        Returns:
            str: 抽出されたJSONコンテンツ
        
        Raises:
            ValueError: JSONブロックが見つからない場合
        """
        # コードブロック内のJSONを検索
        json_block_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', content)
        if json_block_match:
            return json_block_match.group(1).strip()
        
        # コードブロックがない場合、最初の「[」から最後の「]」までを抽出
        if content.strip().startswith('[') and ']' in content:
            return content.strip()
        
        # コードブロックがない場合、最初の「{」から最後の「}」までを抽出
        if content.strip().startswith('{') and '}' in content:
            return content.strip()
        
        # JSONっぽい構造を持つ行のみを抽出
        json_lines = []
        in_json = False
        
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('{') or stripped.startswith('['):
                in_json = True
                json_lines.append(stripped)
            elif in_json and ('}' in stripped or ']' in stripped):
                json_lines.append(stripped)
                if stripped.endswith('}') or stripped.endswith(']'):
                    in_json = False
            elif in_json:
                json_lines.append(stripped)
        
        if json_lines:
            return '\n'.join(json_lines)
        
        raise ValueError("JSONブロックが見つかりませんでした")
    
    def modify_durations(self, script_data: Dict[str, Any], target_total: str = None) -> Dict[str, Any]:
        """
        スクリプトの継続時間を調整する。
        
        Args:
            script_data (dict): 調整するスクリプトデータ
            target_total (str, optional): 目標の総時間（HH:MM:SS形式）
        
        Returns:
            dict: 調整されたスクリプトデータ
        """
        # 目標総時間が指定されていない場合は既存の値を使用
        if not target_total:
            target_total = script_data.get("duration", "00:05:00")
        
        # 既存のシーン継続時間を取得
        scenes = script_data.get("scenes", [])
        if not scenes:
            script_data["duration"] = target_total
            return script_data
        
        # 各シーンの継続時間を秒単位に変換
        scene_durations = []
        for scene in scenes:
            duration = scene.get("duration", "00:01:00")
            # HH:MM:SS形式を秒に変換
            try:
                time_parts = list(map(int, duration.split(":")))
                if len(time_parts) == 3:
                    seconds = time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
                elif len(time_parts) == 2:
                    seconds = time_parts[0] * 60 + time_parts[1]
                else:
                    seconds = time_parts[0]
            except (ValueError, IndexError):
                seconds = 60  # デフォルト1分
            
            scene_durations.append(seconds)
        
        # 現在の総時間
        current_total_seconds = sum(scene_durations)
        
        # 目標総時間を秒に変換
        target_parts = list(map(int, target_total.split(":")))
        if len(target_parts) == 3:
            target_total_seconds = target_parts[0] * 3600 + target_parts[1] * 60 + target_parts[2]
        elif len(target_parts) == 2:
            target_total_seconds = target_parts[0] * 60 + target_parts[1]
        else:
            target_total_seconds = target_parts[0]
        
        # 比率計算
        if current_total_seconds > 0:
            ratio = target_total_seconds / current_total_seconds
        else:
            # 現在の総時間が0の場合は均等に配分
            single_scene_seconds = target_total_seconds / len(scenes)
            ratio = 1
            scene_durations = [single_scene_seconds] * len(scenes)
        
        # 各シーンの時間を調整
        for i, scene in enumerate(scenes):
            new_seconds = int(scene_durations[i] * ratio)
            # 秒を HH:MM:SS 形式に戻す
            hours, remainder = divmod(new_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            scene["duration"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # 総時間を設定
        script_data["duration"] = target_total
        
        return script_data 