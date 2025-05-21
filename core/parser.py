"""
Markdownおよび YAML 形式のテキストを解析するためのモジュール。
コンテンツの構造解析、セクション抽出、画像参照抽出などの機能を提供する。
"""
import re
import yaml


class MarkdownParser:
    """
    Markdown 形式のテキストを解析するクラス。
    主にタイトル、章、セクションの抽出、画像参照の検出などを担当する。
    """

    def parse_markdown(self, content):
        """
        Markdown テキストを解析し、構造化されたデータを返す

        Args:
            content (str): 解析するMarkdownコンテンツ

        Returns:
            dict: タイトル、章、セクションなどの構造化データ
        """
        lines = content.split('\n')
        result = {
            "title": "",
            "chapters": []
        }

        current_chapter = None
        current_section = None

        for line in lines:
            # タイトル（h1）を検出
            title_match = re.match(r'^# (.+)$', line)
            if title_match:
                result["title"] = title_match.group(1).strip()
                continue

            # 章（h2）を検出
            chapter_match = re.match(r'^## (.+)$', line)
            if chapter_match:
                current_chapter = {
                    "title": chapter_match.group(1).strip(),
                    "sections": []
                }
                result["chapters"].append(current_chapter)
                continue

            # セクション（h3）を検出
            section_match = re.match(r'^### (.+)$', line)
            if section_match and current_chapter is not None:
                current_section = {
                    "title": section_match.group(1).strip(),
                    "content": ""
                }
                current_chapter["sections"].append(current_section)
                continue

            # セクションにコンテンツを追加
            if current_section is not None:
                current_section["content"] += line + "\n"

        return result

    def extract_sections(self, content):
        """
        Markdown からすべての見出しレベルとセクションを抽出する

        Args:
            content (str): 解析するMarkdownコンテンツ

        Returns:
            list: 各セクションの情報（レベル、タイトル、開始行）
        """
        sections = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # 見出しパターンを検出
            heading_match = re.match(r'^(#{1,6}) (.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))  # '#' の数がレベル
                title = heading_match.group(2).strip()
                sections.append({
                    "level": level,
                    "title": title,
                    "line": i
                })

        return sections

    def extract_images(self, content):
        """
        Markdown から画像参照を抽出する

        Args:
            content (str): 解析するMarkdownコンテンツ

        Returns:
            list: 画像情報のリスト（タイプ、コンテンツ、位置など）
        """
        images = []
        
        # Mermaidダイアグラムを検出
        mermaid_pattern = r'```mermaid\n(.*?)\n```'
        mermaid_matches = re.finditer(mermaid_pattern, content, re.DOTALL)
        
        for match in mermaid_matches:
            images.append({
                "type": "mermaid",
                "content": match.group(1),
                "start": match.start(),
                "end": match.end()
            })
            
        # 通常の画像参照を検出（今回は実装していません）
        # ![alt text](image_url) 形式の検出など
        
        return images


class YAMLParser:
    """
    YAML 形式のテキストを解析するクラス。
    主にセクション構造、パラグラフ情報、学習目標などの抽出を担当する。
    """

    def parse_yaml(self, content):
        """
        YAML テキストを解析し、Python オブジェクトに変換する

        Args:
            content (str): 解析するYAMLコンテンツ

        Returns:
            dict: 解析されたYAMLデータ
        """
        try:
            data = yaml.safe_load(content)
            return data
        except yaml.YAMLError as e:
            raise ValueError(f"YAML解析エラー: {str(e)}")

    def validate_structure(self, content):
        """
        YAMLの構造が期待される形式に従っているかを検証する

        Args:
            content (str): 検証するYAMLコンテンツ

        Returns:
            bool: 構造が有効な場合はTrue、そうでない場合はFalse

        Raises:
            ValueError: 構造が無効な場合に発生する例外
        """
        try:
            data = yaml.safe_load(content)
            
            # 必須フィールドの存在チェック
            if "title" not in data:
                raise ValueError("YAMLにtitleフィールドがありません")
                
            if "chapters" not in data:
                raise ValueError("YAMLにchaptersフィールドがありません")
                
            # 各章の検証
            for chapter in data["chapters"]:
                if "id" not in chapter:
                    raise ValueError("章にidフィールドがありません")
                if "title" not in chapter:
                    raise ValueError("章にtitleフィールドがありません")
            
            return True
            
        except yaml.YAMLError as e:
            raise ValueError(f"YAML構文エラー: {str(e)}")

    def extract_learning_objectives(self, data):
        """
        YAMLデータから学習目標を抽出する

        Args:
            data (dict): 解析済みのYAMLデータ

        Returns:
            list: 学習目標のリスト
        """
        objectives = []
        
        # すべての章を走査
        for chapter in data.get("chapters", []):
            # 各セクションから学習目標を抽出
            for section in chapter.get("sections", []):
                objectives.extend(section.get("learning_objectives", []))
                
        return objectives 