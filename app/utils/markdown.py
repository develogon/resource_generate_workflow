import re


class MarkdownUtils:
    """Markdown操作ユーティリティクラス

    Markdownの解析と変換を行うユーティリティクラスです。
    """

    @staticmethod
    def extract_heading(markdown_content, level=1):
        """指定レベルの最初の見出しを抽出する

        Args:
            markdown_content (str): Markdownコンテンツ
            level (int, optional): 見出しレベル. デフォルトは1

        Returns:
            str: 見出しテキスト。見つからない場合はNone
        """
        lines = markdown_content.split('\n')
        heading_marker = '#' * level + ' '
        
        for line in lines:
            if line.startswith(heading_marker):
                return line[len(heading_marker):].strip()
        
        return None

    @staticmethod
    def extract_all_headings(markdown_content, max_level=6):
        """すべての見出しを抽出する

        Args:
            markdown_content (str): Markdownコンテンツ
            max_level (int, optional): 最大見出しレベル. デフォルトは6

        Returns:
            list: 見出し情報のリスト。各見出しは辞書形式で返される
                 {'level': int, 'text': str, 'line': int}
        """
        lines = markdown_content.split('\n')
        headings = []
        
        for i, line in enumerate(lines):
            for level in range(1, max_level + 1):
                heading_marker = '#' * level + ' '
                if line.startswith(heading_marker):
                    headings.append({
                        'level': level,
                        'text': line[len(heading_marker):].strip(),
                        'line': i
                    })
                    break
        
        return headings

    @staticmethod
    def generate_toc(markdown_content, max_level=3):
        """目次を生成する

        Args:
            markdown_content (str): Markdownコンテンツ
            max_level (int, optional): 最大見出しレベル. デフォルトは3

        Returns:
            str: 生成された目次
        """
        headings = MarkdownUtils.extract_all_headings(markdown_content, max_level)
        toc_lines = []
        
        for heading in headings:
            indent = '  ' * (heading['level'] - 1)
            toc_lines.append(f"{indent}- {heading['text']}")
        
        return '\n'.join(toc_lines)

    @staticmethod
    def extract_code_blocks(markdown_content, language=None):
        """コードブロックを抽出する

        Args:
            markdown_content (str): Markdownコンテンツ
            language (str, optional): 抽出する言語. デフォルトはNone（すべての言語）

        Returns:
            list: コードブロック情報のリスト。各ブロックは辞書形式で返される
                 {'language': str, 'content': str}
        """
        lines = markdown_content.split('\n')
        code_blocks = []
        current_block = None
        current_language = None
        
        for i, line in enumerate(lines):
            if line.startswith('```'):
                if current_block is None:
                    # 新しいコードブロックの開始
                    current_block = []
                    current_language = line[3:].strip() if len(line) > 3 else None
                    
                    if language is None or current_language == language:
                        continue
                    else:
                        current_block = None
                        current_language = None
                else:
                    # コードブロックの終了
                    if language is None or current_language == language:
                        code_blocks.append({
                            'language': current_language,
                            'content': '\n'.join(current_block)
                        })
                    current_block = None
                    current_language = None
            elif current_block is not None:
                # コードブロック内の行
                current_block.append(line)
        
        return code_blocks

    @staticmethod
    def extract_links(markdown_content):
        """リンクを抽出する

        Args:
            markdown_content (str): Markdownコンテンツ

        Returns:
            list: リンク情報のリスト。各リンクは辞書形式で返される
                 {'text': str, 'url': str}
        """
        links = []
        
        # Markdownリンクのパターン: [テキスト](URL)
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(pattern, markdown_content)
        
        for match in matches:
            links.append({
                'text': match[0],
                'url': match[1]
            })
        
        return links

    @staticmethod
    def convert_to_html(markdown_content):
        """MarkdownをHTMLに変換する

        Args:
            markdown_content (str): Markdownコンテンツ

        Returns:
            str: 変換されたHTMLコンテンツ
        """
        lines = markdown_content.split('\n')
        html_lines = []
        
        for line in lines:
            if line.startswith('# '):
                html_lines.append(f"<h1>{line[2:].strip()}</h1>")
            elif line.startswith('## '):
                html_lines.append(f"<h2>{line[3:].strip()}</h2>")
            elif line.startswith('### '):
                html_lines.append(f"<h3>{line[4:].strip()}</h3>")
            elif line.startswith('- '):
                html_lines.append(f"<li>{line[2:].strip()}</li>")
            elif line.strip() == '':
                html_lines.append("<br>")
            else:
                html_lines.append(f"<p>{line}</p>")
        
        return '\n'.join(html_lines) 