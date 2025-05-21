"""
動画台本生成を担当するモジュール。
Claude APIを使用して台本の生成と構造化を行う。
"""
import re
from typing import Dict, Any, Optional, List, Pattern


class ScriptFormatConfig:
    """台本フォーマット設定クラス"""
    def __init__(
        self,
        required_sections: List[str] = None,
        speaker_patterns: List[str] = None,
        quote_format: str = None
    ):
        """
        台本フォーマット設定を初期化する
        
        Args:
            required_sections: 必須セクション名のリスト (例: ["概要", "ナレーション"])
            speaker_patterns: 話者パターンのリスト (例: ["ナレーター", "解説者"])
            quote_format: 引用符のフォーマット (例: "「{}」")
        """
        self.required_sections = required_sections or ["ナレーション", "スクリプト"]
        self.speaker_patterns = speaker_patterns or ["ナレーター", "解説者", "講師"]
        self.quote_format = quote_format or "「{}」"
        
        # 正規表現パターンの事前コンパイル
        self._speaker_regex = self._compile_speaker_regex()
        
    def _compile_speaker_regex(self) -> Pattern:
        """話者パターンの正規表現をコンパイルする"""
        speaker_pattern = "|".join(map(re.escape, self.speaker_patterns))
        return re.compile(f"^({speaker_pattern})\\s*[:：]\\s*", re.MULTILINE)


from core.content_generator import ContentGenerator


class ScriptGenerator(ContentGenerator):
    """
    動画台本生成を担当するクラス。
    ContentGeneratorを継承し、台本特有の処理を実装する。
    """
    
    def __init__(
        self,
        claude_service: Any,
        file_manager: Any,
        template_dir: str = "templates",
        format_config: ScriptFormatConfig = None
    ):
        """
        ScriptGeneratorを初期化する。
        
        Args:
            claude_service (Any): Claude APIサービス
            file_manager (Any): ファイル管理サービス
            template_dir (str, optional): テンプレートディレクトリのパス
            format_config (ScriptFormatConfig, optional): 台本フォーマット設定
        """
        super().__init__(claude_service, file_manager, template_dir)
        self.format_config = format_config or ScriptFormatConfig()
    
    def format_output(self, raw_content: str) -> str:
        """
        動画台本出力を整形する。
        
        Args:
            raw_content (str): 生成された生の台本内容
        
        Returns:
            str: 整形された台本
        """
        if not raw_content:
            return raw_content
            
        # 余分な空行を圧縮
        content = re.sub(r'\n{3,}', '\n\n', raw_content.strip())
        
        # 台本形式の整形
        for speaker in self.format_config.speaker_patterns:
            # 話者行のフォーマット統一（行頭と行の途中）
            content = re.sub(
                f'(?<=\n){re.escape(speaker)} ?[:：] ?',
                f'{speaker}: ',
                content
            )
            content = re.sub(
                f'^{re.escape(speaker)} ?[:：] ?',
                f'{speaker}: ',
                content
            )
        
        # 見出し間の適切なスペーシング
        content = re.sub(r'(\n## [^\n]+)\n(?!\n)', r'\1\n\n', content)
        
        return content
    
    def validate_content(self, content: str) -> bool:
        """
        生成された台本コンテンツを検証する。
        
        Args:
            content (str): 検証する台本コンテンツ
        
        Returns:
            bool: コンテンツが有効な場合はTrue、そうでない場合はFalse
        """
        if not content or not content.strip():
            return False
        
        # タイトルの確認
        has_title = bool(re.search(r'^#\s+.+', content, re.MULTILINE))
        if not has_title:
            return False
        
        # 必須セクションの確認
        for section in self.format_config.required_sections:
            section_pattern = f'^##\\s+{re.escape(section)}'
            if not re.search(section_pattern, content, re.MULTILINE):
                return False
        
        return True
    
    def structure_script(self, script_content: str) -> str:
        """
        台本の構造を整理する。
        
        Args:
            script_content (str): 構造化する台本コンテンツ
        
        Returns:
            str: 構造化された台本
        """
        # 台本が十分な長さがない場合はそのまま返す
        if not script_content or len(script_content.strip().split('\n')) < 3:
            return script_content
        
        # コンテンツを行に分割
        lines = script_content.strip().split('\n')
        
        # セクションを識別
        structured_content = []
        
        for line in lines:
            # 見出しの場合
            if re.match(r'^#\s+', line) or re.match(r'^##\s+', line):
                structured_content.append(line)
            # 空行の場合
            elif line.strip() == '':
                structured_content.append(line)
            # 通常のコンテンツ行
            else:
                # 話者の台詞行のフォーマットを整える
                speaker_match = self.format_config._speaker_regex.match(line)
                if speaker_match:
                    speaker = speaker_match.group(1)
                    line = re.sub(
                        f'^{re.escape(speaker)}\\s*[:：]\\s*',
                        f'{speaker}: ',
                        line
                    )
                
                structured_content.append(line)
        
        return '\n'.join(structured_content) 