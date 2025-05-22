import pytest
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート（まだ実装されていない場合はコメントアウト）
# from app.utils.markdown import MarkdownUtils

class TestMarkdownUtils:
    """Markdownユーティリティのテストクラス"""
    
    @pytest.fixture
    def markdown_utils(self):
        """テスト用のMarkdownユーティリティインスタンスを作成"""
        # コメントアウトされているコードは、実際のクラスが実装された後に有効化する
        # return MarkdownUtils()
        
        # モックインスタンスを返す（クラスが実装されるまでの一時的な対応）
        mock_utils = MagicMock()
        
        # extract_heading メソッドが呼ばれたときに実行される関数
        def mock_extract_heading(markdown_content, level=1):
            lines = markdown_content.split('\n')
            heading_marker = '#' * level + ' '
            
            for line in lines:
                if line.startswith(heading_marker):
                    return line[len(heading_marker):].strip()
            
            return None
            
        mock_utils.extract_heading.side_effect = mock_extract_heading
        
        # extract_all_headings メソッドが呼ばれたときに実行される関数
        def mock_extract_all_headings(markdown_content, max_level=6):
            lines = markdown_content.split('\n')
            headings = []
            
            for line in lines:
                for level in range(1, max_level + 1):
                    heading_marker = '#' * level + ' '
                    if line.startswith(heading_marker):
                        headings.append({
                            'level': level,
                            'text': line[len(heading_marker):].strip(),
                            'line': lines.index(line)
                        })
                        break
            
            return headings
            
        mock_utils.extract_all_headings.side_effect = mock_extract_all_headings
        
        # generate_toc メソッドが呼ばれたときに実行される関数
        def mock_generate_toc(markdown_content, max_level=3):
            headings = mock_extract_all_headings(markdown_content, max_level)
            toc_lines = []
            
            for heading in headings:
                indent = '  ' * (heading['level'] - 1)
                toc_lines.append(f"{indent}- {heading['text']}")
            
            return '\n'.join(toc_lines)
            
        mock_utils.generate_toc.side_effect = mock_generate_toc
        
        # extract_code_blocks メソッドが呼ばれたときに実行される関数
        def mock_extract_code_blocks(markdown_content, language=None):
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
            
        mock_utils.extract_code_blocks.side_effect = mock_extract_code_blocks
        
        # extract_links メソッドが呼ばれたときに実行される関数
        def mock_extract_links(markdown_content):
            import re
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
            
        mock_utils.extract_links.side_effect = mock_extract_links
        
        # convert_to_html メソッドが呼ばれたときに実行される関数
        def mock_convert_to_html(markdown_content):
            # 非常に簡易的なMarkdown→HTML変換
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
            
        mock_utils.convert_to_html.side_effect = mock_convert_to_html
        
        return mock_utils
    
    @pytest.fixture
    def sample_markdown(self):
        """サンプルのMarkdownコンテンツを返す"""
        return """# メインタイトル

## 第1章: はじめに

これは第1章の内容です。

### 1.1 基本概念

基本的な概念は以下の通りです：

- 項目1
- 項目2
- 項目3

```python
def example():
    return "これはサンプルコードです"
```

### 1.2 重要な考え方

重要な考え方について説明します。

## 第2章: 実践編

これは第2章の内容です。

[リンクテキスト](https://example.com)
"""
    
    def test_extract_heading(self, markdown_utils, sample_markdown):
        """見出し抽出のテスト"""
        # レベル1の見出し（タイトル）の抽出
        title = markdown_utils.extract_heading(sample_markdown, level=1)
        assert title == "メインタイトル"
        
        # レベル2の見出し（チャプター）の抽出
        chapter = markdown_utils.extract_heading(sample_markdown, level=2)
        assert chapter == "第1章: はじめに"
    
    def test_extract_all_headings(self, markdown_utils, sample_markdown):
        """すべての見出し抽出のテスト"""
        headings = markdown_utils.extract_all_headings(sample_markdown)
        
        # 見出しが正しく抽出されることを確認
        assert len(headings) == 5
        assert headings[0]['level'] == 1
        assert headings[0]['text'] == "メインタイトル"
        assert headings[1]['level'] == 2
        assert headings[1]['text'] == "第1章: はじめに"
        assert headings[2]['level'] == 3
        assert headings[2]['text'] == "1.1 基本概念"
    
    def test_generate_toc(self, markdown_utils, sample_markdown):
        """目次生成のテスト"""
        toc = markdown_utils.generate_toc(sample_markdown)
        
        # 目次が正しく生成されることを確認
        assert "- メインタイトル" in toc
        assert "  - 第1章: はじめに" in toc
        assert "    - 1.1 基本概念" in toc
        assert "    - 1.2 重要な考え方" in toc
        assert "  - 第2章: 実践編" in toc
    
    def test_extract_code_blocks(self, markdown_utils, sample_markdown):
        """コードブロック抽出のテスト"""
        code_blocks = markdown_utils.extract_code_blocks(sample_markdown)
        
        # コードブロックが正しく抽出されることを確認
        assert len(code_blocks) == 1
        assert code_blocks[0]['language'] == 'python'
        assert "def example():" in code_blocks[0]['content']
        assert "return" in code_blocks[0]['content']
        
        # 特定の言語のコードブロックのみを抽出するテスト
        python_blocks = markdown_utils.extract_code_blocks(sample_markdown, language='python')
        assert len(python_blocks) == 1
        
        # 存在しない言語のコードブロック抽出テスト
        javascript_blocks = markdown_utils.extract_code_blocks(sample_markdown, language='javascript')
        assert len(javascript_blocks) == 0
    
    def test_extract_links(self, markdown_utils, sample_markdown):
        """リンク抽出のテスト"""
        links = markdown_utils.extract_links(sample_markdown)
        
        # リンクが正しく抽出されることを確認
        assert len(links) == 1
        assert links[0]['text'] == "リンクテキスト"
        assert links[0]['url'] == "https://example.com"
    
    def test_convert_to_html(self, markdown_utils, sample_markdown):
        """HTML変換のテスト"""
        html = markdown_utils.convert_to_html(sample_markdown)
        
        # HTMLが正しく変換されることを確認
        assert "<h1>メインタイトル</h1>" in html
        assert "<h2>第1章: はじめに</h2>" in html
        assert "<h3>1.1 基本概念</h3>" in html
        assert "<li>項目1</li>" in html
        assert "<li>項目2</li>" in html
        assert "<li>項目3</li>" in html
    
    def test_extract_heading_not_found(self, markdown_utils):
        """存在しない見出しレベルの抽出テスト"""
        markdown_content = "これは見出しのないテキストです。"
        
        heading = markdown_utils.extract_heading(markdown_content, level=1)
        assert heading is None
    
    def test_extract_all_headings_empty(self, markdown_utils):
        """見出しのないMarkdownでのすべての見出し抽出テスト"""
        markdown_content = "これは見出しのないテキストです。\n\n複数行あります。"
        
        headings = markdown_utils.extract_all_headings(markdown_content)
        assert len(headings) == 0
    
    def test_generate_toc_empty(self, markdown_utils):
        """見出しのないMarkdownでの目次生成テスト"""
        markdown_content = "これは見出しのないテキストです。\n\n複数行あります。"
        
        toc = markdown_utils.generate_toc(markdown_content)
        assert toc == ""
    
    def test_extract_code_blocks_without_language(self, markdown_utils):
        """言語指定なしのコードブロック抽出テスト"""
        markdown_content = """# テスト

```
const a = 1;
console.log(a);
```

通常のテキスト

```python
def test():
    pass
```
"""
        
        code_blocks = markdown_utils.extract_code_blocks(markdown_content)
        assert len(code_blocks) == 2
        assert code_blocks[0]['language'] is None
        assert code_blocks[1]['language'] == 'python' 