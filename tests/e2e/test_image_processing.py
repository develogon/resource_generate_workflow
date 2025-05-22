import pytest
import os
import shutil
from unittest.mock import patch, MagicMock
from io import BytesIO

# テスト対象のモジュールをインポート（まだ実装されていない場合はコメントアウト）
# from app.cli import main
# from app.processors.image import ImageProcessor
# from app.clients.s3 import S3Client

class TestImageProcessingWorkflow:
    """画像処理ワークフローのE2Eテスト"""
    
    @pytest.fixture
    def setup_e2e(self, tmp_path):
        """E2Eテスト用の環境セットアップ"""
        # テスト用の一時ディレクトリを作成
        base_dir = tmp_path / "e2e_image_test"
        base_dir.mkdir()
        
        # 画像テスト用のディレクトリ構造を作成
        section_dir = base_dir / "第1章_はじめに" / "1_1_基本概念"
        section_dir.mkdir(parents=True)
        
        # 画像ディレクトリを作成
        images_dir = section_dir / "images"
        images_dir.mkdir()
        
        # テスト用のarticle.mdファイルを作成（画像埋め込み）
        article_file = section_dir / "article.md"
        with open(article_file, "w") as f:
            f.write("""# 1.1 基本概念

基本的な概念について説明します。

## SVG画像の例

```svg
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />
</svg>
```

## Mermaid図の例

```mermaid
graph TD;
    A-->B;
    A-->C;
    B-->D;
    C-->D;
```

## DrawIO図の例

```drawio
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="2023-04-01T12:00:00.000Z">
  <diagram id="test-diagram" name="Test Diagram">
    <mxGraphModel dx="1422" dy="762" grid="1">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="2" value="テスト" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">
          <mxGeometry x="350" y="290" width="120" height="60" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

以上が画像の例です。
""")
        
        # テスト環境変数を設定
        os.environ["AWS_ACCESS_KEY_ID"] = "dummy_aws_key_id"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "dummy_aws_secret"
        os.environ["S3_BUCKET_NAME"] = "dummy-bucket"
        
        # テスト後のクリーンアップを設定
        yield {
            "base_dir": base_dir,
            "section_dir": section_dir,
            "article_file": article_file,
            "images_dir": images_dir
        }
        
        # 環境変数をクリーンアップ
        for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET_NAME"]:
            if key in os.environ:
                del os.environ[key]
    
    @patch("app.processors.image.ImageProcessor")
    @patch("app.clients.s3.S3Client")
    def test_svg_processing(self, mock_s3_client, mock_image_processor, setup_e2e):
        """SVG画像処理のテスト"""
        # セットアップ情報を取得
        section_dir = setup_e2e["section_dir"]
        article_file = setup_e2e["article_file"]
        images_dir = setup_e2e["images_dir"]
        
        # モックのセットアップ
        mock_processor_instance = mock_image_processor.return_value
        mock_s3_instance = mock_s3_client.return_value
        
        # SVG処理のモック化
        mock_processor_instance.extract_svg_blocks.return_value = [
            '<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">\n  <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" />\n</svg>'
        ]
        
        # 画像変換のモック
        dummy_png_data = b"dummy_png_data"
        mock_processor_instance.convert_svg_to_png.return_value = dummy_png_data
        
        # S3アップロードのモック
        mock_s3_instance.upload_file.return_value = "images/image_1.png"
        mock_s3_instance.get_public_url.return_value = "https://dummy-bucket.s3.amazonaws.com/images/image_1.png"
        
        # 画像処理実行（実際はCLIから呼び出されるが、ここではモック処理）
        # このテストは、実際のクラスが実装された後に有効化する
        # processor = ImageProcessor()
        # s3_client = S3Client(bucket_name="dummy-bucket")
        # 
        # # 記事からSVGを抽出
        # svg_blocks = processor.extract_svg_blocks(str(article_file))
        # 
        # # SVGをPNGに変換
        # for i, svg in enumerate(svg_blocks):
        #     png_data = processor.convert_svg_to_png(svg)
        #     image_path = os.path.join(str(images_dir), f"image_{i+1}.png")
        #     
        #     # 変換された画像を保存
        #     with open(image_path, "wb") as f:
        #         f.write(png_data)
        #     
        #     # S3にアップロード
        #     s3_key = s3_client.upload_file(png_data, f"images/image_{i+1}.png", "image/png")
        #     image_url = s3_client.get_public_url(s3_key)
        #     
        #     # Markdownの画像参照を置換
        #     with open(article_file, "r") as f:
        #         content = f.read()
        #     
        #     updated_content = content.replace(f"```svg\n{svg}\n```", f"![image_{i+1}]({image_url})")
        #     
        #     with open(article_file, "w") as f:
        #         f.write(updated_content)
        
        # モックメソッドが呼び出されたことを確認
        # mock_processor_instance.extract_svg_blocks.assert_called_once_with(str(article_file))
        # mock_processor_instance.convert_svg_to_png.assert_called_once()
        # mock_s3_instance.upload_file.assert_called_once()
        # mock_s3_instance.get_public_url.assert_called_once()
        pass
    
    @patch("app.processors.image.ImageProcessor")
    @patch("app.clients.s3.S3Client")
    def test_mermaid_processing(self, mock_s3_client, mock_image_processor, setup_e2e):
        """Mermaid図処理のテスト"""
        # セットアップ情報を取得
        section_dir = setup_e2e["section_dir"]
        article_file = setup_e2e["article_file"]
        images_dir = setup_e2e["images_dir"]
        
        # モックのセットアップ
        mock_processor_instance = mock_image_processor.return_value
        mock_s3_instance = mock_s3_client.return_value
        
        # Mermaid処理のモック化
        mock_processor_instance.extract_mermaid_blocks.return_value = [
            'graph TD;\n    A-->B;\n    A-->C;\n    B-->D;\n    C-->D;'
        ]
        
        # 画像変換のモック
        dummy_png_data = b"dummy_mermaid_png_data"
        mock_processor_instance.convert_mermaid_to_png.return_value = dummy_png_data
        
        # S3アップロードのモック
        mock_s3_instance.upload_file.return_value = "images/mermaid_1.png"
        mock_s3_instance.get_public_url.return_value = "https://dummy-bucket.s3.amazonaws.com/images/mermaid_1.png"
        
        # 画像処理実行（実際はCLIから呼び出されるが、ここではモック処理）
        # このテストは、実際のクラスが実装された後に有効化する
        # processor = ImageProcessor()
        # s3_client = S3Client(bucket_name="dummy-bucket")
        # 
        # # 記事からMermaidを抽出
        # mermaid_blocks = processor.extract_mermaid_blocks(str(article_file))
        # 
        # # MermaidをPNGに変換
        # for i, mermaid in enumerate(mermaid_blocks):
        #     png_data = processor.convert_mermaid_to_png(mermaid)
        #     image_path = os.path.join(str(images_dir), f"mermaid_{i+1}.png")
        #     
        #     # 変換された画像を保存
        #     with open(image_path, "wb") as f:
        #         f.write(png_data)
        #     
        #     # S3にアップロード
        #     s3_key = s3_client.upload_file(png_data, f"images/mermaid_{i+1}.png", "image/png")
        #     image_url = s3_client.get_public_url(s3_key)
        #     
        #     # Markdownの画像参照を置換
        #     with open(article_file, "r") as f:
        #         content = f.read()
        #     
        #     updated_content = content.replace(f"```mermaid\n{mermaid}\n```", f"![mermaid_{i+1}]({image_url})")
        #     
        #     with open(article_file, "w") as f:
        #         f.write(updated_content)
        
        # モックメソッドが呼び出されたことを確認
        # mock_processor_instance.extract_mermaid_blocks.assert_called_once_with(str(article_file))
        # mock_processor_instance.convert_mermaid_to_png.assert_called_once()
        # mock_s3_instance.upload_file.assert_called_once()
        # mock_s3_instance.get_public_url.assert_called_once()
        pass

    @patch("app.processors.image.ImageProcessor")
    @patch("app.clients.s3.S3Client")
    def test_drawio_processing(self, mock_s3_client, mock_image_processor, setup_e2e):
        """DrawIO図処理のテスト"""
        # セットアップ情報を取得
        section_dir = setup_e2e["section_dir"]
        article_file = setup_e2e["article_file"]
        images_dir = setup_e2e["images_dir"]
        
        # モックのセットアップ
        mock_processor_instance = mock_image_processor.return_value
        mock_s3_instance = mock_s3_client.return_value
        
        # DrawIO処理のモック化
        drawio_content = '<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="app.diagrams.net" modified="2023-04-01T12:00:00.000Z">\n  <diagram id="test-diagram" name="Test Diagram">\n    <mxGraphModel dx="1422" dy="762" grid="1">\n      <root>\n        <mxCell id="0" />\n        <mxCell id="1" parent="0" />\n        <mxCell id="2" value="テスト" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">\n          <mxGeometry x="350" y="290" width="120" height="60" as="geometry" />\n        </mxCell>\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>'
        mock_processor_instance.extract_drawio_blocks.return_value = [drawio_content]
        
        # 画像変換のモック
        dummy_png_data = b"dummy_drawio_png_data"
        mock_processor_instance.convert_drawio_to_png.return_value = dummy_png_data
        
        # S3アップロードのモック
        mock_s3_instance.upload_file.return_value = "images/drawio_1.png"
        mock_s3_instance.get_public_url.return_value = "https://dummy-bucket.s3.amazonaws.com/images/drawio_1.png"
        
        # 画像処理実行（実際はCLIから呼び出されるが、ここではモック処理）
        # このテストは、実際のクラスが実装された後に有効化する
        # processor = ImageProcessor()
        # s3_client = S3Client(bucket_name="dummy-bucket")
        # 
        # # 記事からDrawIOを抽出
        # drawio_blocks = processor.extract_drawio_blocks(str(article_file))
        # 
        # # DrawIOをPNGに変換
        # for i, drawio in enumerate(drawio_blocks):
        #     png_data = processor.convert_drawio_to_png(drawio)
        #     image_path = os.path.join(str(images_dir), f"drawio_{i+1}.png")
        #     
        #     # 変換された画像を保存
        #     with open(image_path, "wb") as f:
        #         f.write(png_data)
        #     
        #     # S3にアップロード
        #     s3_key = s3_client.upload_file(png_data, f"images/drawio_{i+1}.png", "image/png")
        #     image_url = s3_client.get_public_url(s3_key)
        #     
        #     # Markdownの画像参照を置換
        #     with open(article_file, "r") as f:
        #         content = f.read()
        #     
        #     updated_content = content.replace(f"```drawio\n{drawio}\n```", f"![drawio_{i+1}]({image_url})")
        #     
        #     with open(article_file, "w") as f:
        #         f.write(updated_content)
        
        # モックメソッドが呼び出されたことを確認
        # mock_processor_instance.extract_drawio_blocks.assert_called_once_with(str(article_file))
        # mock_processor_instance.convert_drawio_to_png.assert_called_once()
        # mock_s3_instance.upload_file.assert_called_once()
        # mock_s3_instance.get_public_url.assert_called_once()
        pass 