import pytest
import os

pytest.importorskip("app.utils.markdown", reason="Utils modules are not yet implemented")

from app.utils.markdown import extract_headings, extract_images, combine_markdown
from app.utils.file import ensure_dir, read_file, write_file
from app.utils.logger import get_logger


def test_extract_headings():
    """マークダウンから見出しを抽出するテスト"""
    content = """
    # メインタイトル
    
    テキスト
    
    ## セクション1
    
    セクション内容
    
    ### サブセクション1.1
    
    サブセクションの内容
    
    ## セクション2
    """
    
    headings = extract_headings(content)
    assert len(headings) == 4  # 全見出し数
    assert headings[0]["level"] == 1  # 最初は#
    assert headings[0]["text"] == "メインタイトル"
    assert headings[1]["level"] == 2  # 次は##
    assert headings[1]["text"] == "セクション1"
    assert headings[3]["text"] == "セクション2"


def test_extract_images():
    """マークダウンから画像参照を抽出するテスト"""
    content = """
    # タイトル
    
    以下は画像です:
    
    ![SVG画像](./image.svg)
    
    次の画像:
    
    ![DrawIO図](./diagram.drawio.svg)
    
    そして最後の画像:
    
    ```mermaid
    graph TD;
        A-->B;
    ```
    """
    
    images = extract_images(content)
    assert len(images) == 3
    assert any(img["path"] == "./image.svg" for img in images)
    assert any(img["path"] == "./diagram.drawio.svg" for img in images)
    assert any(img["type"] == "mermaid" for img in images)


def test_combine_markdown():
    """複数のマークダウンファイルを結合するテスト"""
    content1 = "# ファイル1\n\nコンテンツ1"
    content2 = "# ファイル2\n\nコンテンツ2"
    
    combined = combine_markdown([content1, content2])
    assert "# ファイル1" in combined
    assert "コンテンツ1" in combined
    assert "# ファイル2" in combined
    assert "コンテンツ2" in combined


def test_ensure_dir(tmp_path):
    """ディレクトリが存在することを確認するテスト"""
    test_dir = os.path.join(tmp_path, "test_subdir", "nested")
    
    # まだ存在しないはず
    assert not os.path.exists(test_dir)
    
    # 作成
    ensure_dir(test_dir)
    
    # 今度は存在するはず
    assert os.path.exists(test_dir)
    assert os.path.isdir(test_dir)
    
    # 既に存在する場合もエラーにならない
    ensure_dir(test_dir)
    assert os.path.exists(test_dir)


def test_read_write_file(tmp_path):
    """ファイルの読み書きテスト"""
    test_file = os.path.join(tmp_path, "test.txt")
    content = "テストコンテンツ\n複数行"
    
    # 書き込み
    write_file(test_file, content)
    
    # 存在確認
    assert os.path.exists(test_file)
    
    # 読み込み
    read_content = read_file(test_file)
    assert read_content == content


def test_logger():
    """ロガーが正しく取得できることを確認"""
    logger = get_logger("test_module")
    assert logger is not None
    
    # 同じ名前で2回呼び出しても同じロガーが返ることを確認
    logger2 = get_logger("test_module")
    assert logger is logger2 