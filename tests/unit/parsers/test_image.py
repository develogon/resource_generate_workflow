"""画像・図表検出システムのテスト."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.parsers.image import DetectedDiagram, DetectedImage, ImageDetector


class TestDetectedImage:
    """DetectedImageのテスト."""
    
    def test_initialization_basic(self):
        """基本的な初期化のテスト."""
        image = DetectedImage(
            alt_text="テスト画像",
            url="test.png",
            title="テストタイトル"
        )
        
        assert image.alt_text == "テスト画像"
        assert image.url == "test.png"
        assert image.title == "テストタイトル"
        assert image.file_extension == ".png"
        assert image.is_local is True
        assert image.image_type in ["diagram", "unknown"]
    
    def test_file_extension_detection(self):
        """ファイル拡張子検出のテスト."""
        test_cases = [
            ("image.jpg", ".jpg"),
            ("photo.jpeg", ".jpeg"),
            ("diagram.png", ".png"),
            ("icon.svg", ".svg"),
            ("animation.gif", ".gif"),
            ("modern.webp", ".webp"),
            ("noextension", ""),
            ("image.PNG", ".png"),  # 大文字小文字
        ]
        
        for url, expected_ext in test_cases:
            image = DetectedImage(alt_text="test", url=url)
            assert image.file_extension == expected_ext
    
    def test_local_remote_detection(self):
        """ローカル/リモート判定のテスト."""
        test_cases = [
            ("local.png", True),
            ("./images/local.png", True),
            ("../assets/local.png", True),
            ("http://example.com/remote.png", False),
            ("https://example.com/remote.png", False),
            ("//cdn.example.com/remote.png", False),
        ]
        
        for url, expected_local in test_cases:
            image = DetectedImage(alt_text="test", url=url)
            assert image.is_local == expected_local
    
    def test_image_type_determination_by_extension(self):
        """拡張子による画像タイプ判定のテスト."""
        test_cases = [
            ("photo.jpg", "photo"),
            ("photo.jpeg", "photo"),
            ("diagram.png", "diagram"),
            ("icon.svg", "vector"),
            ("animation.gif", "animation"),
            ("modern.webp", "modern"),
        ]
        
        for url, expected_type in test_cases:
            image = DetectedImage(alt_text="test", url=url)
            assert image.image_type == expected_type
    
    def test_image_type_determination_by_content(self):
        """内容による画像タイプ判定のテスト."""
        test_cases = [
            ("diagram.png", "System Diagram", "diagram"),
            ("chart.png", "Performance Chart", "diagram"),
            ("screen.png", "Screenshot of application", "screenshot"),
            ("capture.png", "Screen capture", "screenshot"),
            ("unknown.png", "Some image", "diagram"),  # pngなのでdiagram
        ]
        
        for url, alt_text, expected_type in test_cases:
            image = DetectedImage(alt_text=alt_text, url=url)
            assert image.image_type == expected_type
    
    def test_determine_image_type_unknown(self):
        """不明な画像タイプの判定テスト."""
        image = DetectedImage(alt_text="test", url="unknown.xyz")
        # 拡張子が不明でキーワードもない場合
        assert image.image_type == "unknown"


class TestDetectedDiagram:
    """DetectedDiagramのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        diagram = DetectedDiagram(
            diagram_type="mermaid",
            content="graph TD\n  A --> B",
            language="mermaid",
            title="テスト図表",
            description="テスト図表の説明",
            source_line=10
        )
        
        assert diagram.diagram_type == "mermaid"
        assert diagram.content == "graph TD\n  A --> B"
        assert diagram.language == "mermaid"
        assert diagram.title == "テスト図表"
        assert diagram.description == "テスト図表の説明"
        assert diagram.source_line == 10
        assert diagram.metadata == {}


class TestImageDetector:
    """ImageDetectorのテスト."""
    
    @pytest.fixture
    def detector(self):
        """ImageDetectorフィクスチャ."""
        return ImageDetector()
    
    @pytest.fixture
    def sample_content_with_images(self):
        """画像を含むサンプルコンテンツ."""
        return """# テストドキュメント

## 画像セクション

![ローカル画像](local.png "ローカル画像のタイトル")

![リモート画像](https://example.com/remote.jpg)

<img src="html-image.gif" alt="HTML画像" title="HTMLタイトル">

## 図表セクション

```mermaid
graph TD
    A[開始] --> B[処理]
    B --> C[終了]
```

```plantuml
@startuml
Alice -> Bob: メッセージ
@enduml
```

```dot
digraph G {
    A -> B;
}
```

```graphviz
graph G {
    node1 -- node2;
}
```

## 通常のコードブロック

```python
print("Hello, World!")
```
"""
    
    def test_initialization(self, detector):
        """初期化のテスト."""
        assert detector.base_path == Path('.')
        assert detector.detected_images == []
        assert detector.detected_diagrams == []
    
    def test_initialization_with_base_path(self):
        """ベースパス指定初期化のテスト."""
        base_path = Path("/tmp/test")
        detector = ImageDetector(base_path)
        assert detector.base_path == base_path
    
    def test_detect_markdown_images(self, detector):
        """Markdown画像検出のテスト."""
        content = """
![テスト画像1](image1.png)
![テスト画像2](image2.jpg "画像2のタイトル")
![](image3.gif)
"""
        
        result = detector.detect_in_content(content)
        
        assert len(result["images"]) == 3
        
        # 1つ目の画像
        img1 = result["images"][0]
        assert img1.alt_text == "テスト画像1"
        assert img1.url == "image1.png"
        assert img1.title == ""
        assert img1.metadata["format"] == "markdown"
        
        # 2つ目の画像
        img2 = result["images"][1]
        assert img2.alt_text == "テスト画像2"
        assert img2.url == "image2.jpg"
        assert img2.title == "画像2のタイトル"
        
        # 3つ目の画像（alt textなし）
        img3 = result["images"][2]
        assert img3.alt_text == ""
        assert img3.url == "image3.gif"
    
    def test_detect_html_images(self, detector):
        """HTML画像検出のテスト."""
        content = """
<img src="image1.png" alt="HTML画像1">
<img src="image2.jpg" alt="HTML画像2" title="HTML画像2のタイトル">
<img src="image3.gif">
<IMG SRC="image4.png" ALT="大文字タグ">
"""
        
        result = detector.detect_in_content(content)
        
        assert len(result["images"]) == 4
        
        # 1つ目の画像
        img1 = result["images"][0]
        assert img1.url == "image1.png"
        assert img1.alt_text == "HTML画像1"
        assert img1.metadata["format"] == "html"
        
        # 2つ目の画像
        img2 = result["images"][1]
        assert img2.url == "image2.jpg"
        assert img2.alt_text == "HTML画像2"
        assert img2.title == "HTML画像2のタイトル"
        
        # 3つ目の画像（alt textなし）
        img3 = result["images"][2]
        assert img3.url == "image3.gif"
        assert img3.alt_text == ""
        
        # 4つ目の画像（大文字タグ）
        img4 = result["images"][3]
        assert img4.url == "image4.png"
        assert img4.alt_text == "大文字タグ"
    
    def test_detect_mermaid_diagrams(self, detector):
        """Mermaid図表検出のテスト."""
        content = """
```mermaid
graph TD
    A[開始] --> B[処理]
    B --> C[終了]
```

```mermaid
sequenceDiagram
    Alice->>Bob: Hello
    Bob-->>Alice: Hi
```
"""
        
        result = detector.detect_in_content(content)
        
        assert len(result["diagrams"]) == 2
        
        # 1つ目の図表
        diagram1 = result["diagrams"][0]
        assert diagram1.diagram_type == "mermaid"
        assert "graph TD" in diagram1.content
        assert "A[開始] --> B[処理]" in diagram1.content
        
        # 2つ目の図表
        diagram2 = result["diagrams"][1]
        assert diagram2.diagram_type == "mermaid"
        assert "sequenceDiagram" in diagram2.content
    
    def test_detect_plantuml_diagrams(self, detector):
        """PlantUML図表検出のテスト."""
        content = """
```plantuml
@startuml
Alice -> Bob: Authentication Request
Bob --> Alice: Authentication Response
@enduml
```
"""
        
        result = detector.detect_in_content(content)
        
        assert len(result["diagrams"]) == 1
        diagram = result["diagrams"][0]
        assert diagram.diagram_type == "plantuml"
        assert "@startuml" in diagram.content
        assert "Alice -> Bob" in diagram.content
    
    def test_detect_graphviz_diagrams(self, detector):
        """Graphviz図表検出のテスト."""
        content = """
```dot
digraph G {
    A -> B -> C;
    B -> D;
}
```

```graphviz
graph G {
    A -- B -- C;
    B -- D;
}
```
"""
        
        result = detector.detect_in_content(content)
        
        assert len(result["diagrams"]) == 2
        
        # 1つ目（dot）
        diagram1 = result["diagrams"][0]
        assert diagram1.diagram_type == "graphviz"
        assert "digraph G" in diagram1.content
        
        # 2つ目（graphviz）
        diagram2 = result["diagrams"][1]
        assert diagram2.diagram_type == "graphviz"
        assert "graph G" in diagram2.content
    
    def test_detect_in_content_comprehensive(self, detector, sample_content_with_images):
        """包括的なコンテンツ検出テスト."""
        result = detector.detect_in_content(sample_content_with_images)
        
        # 画像の検出確認
        assert len(result["images"]) == 3  # Markdown 2個 + HTML 1個
        
        # 図表の検出確認
        assert len(result["diagrams"]) == 4  # mermaid, plantuml, dot, graphviz
        
        # サマリーの確認
        summary = result["summary"]
        assert summary["total_images"] == 3
        assert summary["local_images"] == 2  # ローカル画像
        assert summary["remote_images"] == 1  # リモート画像
        assert summary["total_diagrams"] == 4
        assert "mermaid" in summary["diagram_types"]
        assert "plantuml" in summary["diagram_types"]
        assert "graphviz" in summary["diagram_types"]
    
    def test_verify_local_images_existing(self, detector):
        """存在するローカル画像の検証テスト."""
        # 一時ファイル作成
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            
        try:
            content = f"![テスト画像]({temp_path.name})"
            
            # ベースパスを一時ファイルのディレクトリに設定
            detector.base_path = temp_path.parent
            
            result = detector.detect_in_content(content)
            
            # 画像が存在することを確認
            assert len(result["images"]) == 1
            assert result["images"][0].exists is True
            assert result["summary"]["existing_images"] == 1
            assert result["summary"]["missing_images"] == 0
            
        finally:
            temp_path.unlink()
    
    def test_verify_local_images_missing(self, detector):
        """存在しないローカル画像の検証テスト."""
        content = "![存在しない画像](nonexistent.png)"
        
        result = detector.detect_in_content(content)
        
        assert len(result["images"]) == 1
        assert result["images"][0].exists is False
        assert result["summary"]["existing_images"] == 0
        assert result["summary"]["missing_images"] == 1
    
    def test_verify_remote_images(self, detector):
        """リモート画像の検証テスト."""
        content = "![リモート画像](https://example.com/image.png)"
        
        result = detector.detect_in_content(content)
        
        assert len(result["images"]) == 1
        assert result["images"][0].is_local is False
        assert result["summary"]["remote_images"] == 1
        assert result["summary"]["local_images"] == 0
    
    def test_analyze_image_usage(self, detector, sample_content_with_images):
        """画像使用状況分析のテスト."""
        detector.detect_in_content(sample_content_with_images)
        
        analysis = detector.analyze_image_usage()
        
        assert "total_count" in analysis
        assert "format_distribution" in analysis
        assert "type_distribution" in analysis
        assert "local_vs_remote" in analysis
        assert "file_extensions" in analysis
        assert "size_analysis" in analysis
        
        # 具体的な値の確認
        assert analysis["total_count"] > 0
        assert "markdown" in analysis["format_distribution"]
        assert "html" in analysis["format_distribution"]
    
    def test_get_optimization_suggestions(self, detector):
        """最適化提案のテスト."""
        content = """
![大きな画像](large-image.jpg)
![存在しない画像](missing.png)
![リモート画像](http://example.com/image.png)
<img src="old-format.gif" alt="古い形式">
"""
        
        detector.detect_in_content(content)
        suggestions = detector.get_optimization_suggestions()
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # 具体的な提案内容の確認（実装に依存）
        suggestion_text = " ".join(suggestions)
        # 存在しない画像に関する提案があるか確認（例）
        assert any("missing" in s.lower() or "存在しない" in s for s in suggestions)
    
    def test_empty_content(self, detector):
        """空のコンテンツのテスト."""
        result = detector.detect_in_content("")
        
        assert result["images"] == []
        assert result["diagrams"] == []
        assert result["summary"]["total_images"] == 0
        assert result["summary"]["total_diagrams"] == 0
    
    def test_content_without_images_or_diagrams(self, detector):
        """画像・図表のないコンテンツのテスト."""
        content = """
# タイトル

これは普通のテキストです。

```python
print("Hello, World!")
```

**太字のテキスト**です。
"""
        
        result = detector.detect_in_content(content)
        
        assert result["images"] == []
        assert result["diagrams"] == []
        assert result["summary"]["total_images"] == 0
        assert result["summary"]["total_diagrams"] == 0
    
    def test_line_number_tracking(self, detector):
        """行番号追跡のテスト."""
        content = """行1
行2
![画像1](image1.png)
行4
行5
<img src="image2.jpg" alt="画像2">
行7
```mermaid
graph TD
    A --> B
```
行12
"""
        
        result = detector.detect_in_content(content)
        
        # 画像の行番号確認
        assert result["images"][0].metadata["source_line"] == 3
        assert result["images"][1].metadata["source_line"] == 6
        
        # 図表の行番号確認
        assert result["diagrams"][0].source_line == 8
    
    def test_malformed_syntax(self, detector):
        """不正な構文のテスト."""
        content = """
![不完全な画像](
<img src="incomplete
```mermaid
不完全な図表
"""
        
        # エラーが発生せずに処理されることを確認
        result = detector.detect_in_content(content)
        
        # 正常にパースできるものだけが検出される
        assert isinstance(result["images"], list)
        assert isinstance(result["diagrams"], list)
        assert isinstance(result["summary"], dict)
    
    def test_complex_image_paths(self, detector):
        """複雑な画像パスのテスト."""
        content = """
![相対パス](./images/relative.png)
![親ディレクトリ](../assets/parent.png)
![絶対パス](/usr/local/images/absolute.png)
![スペース付きパス](path with spaces.png)
![日本語パス](画像/テスト.png)
"""
        
        result = detector.detect_in_content(content)
        
        assert len(result["images"]) == 5
        
        # 各パスが正しく検出されているか確認
        urls = [img.url for img in result["images"]]
        assert "./images/relative.png" in urls
        assert "../assets/parent.png" in urls
        assert "/usr/local/images/absolute.png" in urls
        assert "path with spaces.png" in urls
        assert "画像/テスト.png" in urls 