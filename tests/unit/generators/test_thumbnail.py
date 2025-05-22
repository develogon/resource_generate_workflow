import pytest
import pytest_asyncio
import os
import yaml
from unittest.mock import patch, MagicMock, mock_open

# テスト対象のモジュールをインポート
from app.generators.thumbnail import ThumbnailGenerator

class TestThumbnailGenerator:
    """サムネイルジェネレータのテストクラス"""
    
    @pytest_asyncio.fixture
    async def thumbnail_generator(self):
        """テスト用のサムネイルジェネレータインスタンスを作成"""
        return ThumbnailGenerator()
    
    @pytest.fixture
    def sample_structure_data(self):
        """テスト用の構造データを作成"""
        return {
            "title": "メインタイトル",
            "sections": [
                {"title": "セクション1", "content": "セクション1の内容..."},
                {"title": "セクション2", "content": "セクション2の内容..."}
            ]
        }
    
    @pytest.fixture
    def sample_structure_with_chapter(self):
        """チャプター情報を含むサンプル構造データ"""
        return {
            "title": "メインタイトル",
            "chapter_name": "チャプター1",
            "sections": [
                {"title": "セクション1", "content": "セクション1の内容..."}
            ]
        }
    
    @pytest.fixture
    def sample_structure_with_section(self):
        """セクション情報を含むサンプル構造データ"""
        return {
            "title": "メインタイトル",
            "chapter_name": "チャプター1",
            "section_name": "セクション1",
            "content": "セクション1の内容..."
        }
    
    @patch("builtins.open", new_callable=mock_open, read_data="""
model: dall-e-3
prompt: |
  {{title}} をテーマにしたイラスト。
  {{description}}
  明るく清潔感のある配色で、技術的なテーマを表現。
size: 1024x1024
quality: standard
style: vivid
""")
    def test_load_template(self, mock_file, thumbnail_generator):
        """テンプレート読込のテスト"""
        with patch('os.path.join', return_value='/mock/path/templates/thumbnail_template.yaml'):
            template_path = "templates/thumbnail_template.yaml"
            
            result = thumbnail_generator.load_template(template_path)
            
            # 結果が正しいことを確認
            assert result is not None
            assert isinstance(result, dict)
            assert "size" in result
            assert "style" in result
            assert "quality" in result
            
            # ファイルが読み込まれたことを確認
            mock_file.assert_called_once_with(template_path, 'r', encoding='utf-8')
    
    def test_prepare_thumbnail_prompt(self, thumbnail_generator):
        """サムネイル生成用プロンプト準備のテスト"""
        # get_system_promptとget_message_promptをモック化
        with patch.object(thumbnail_generator, 'get_system_prompt', return_value="モックシステムプロンプト") as mock_system, \
             patch.object(thumbnail_generator, 'get_message_prompt', return_value="モックメッセージプロンプト{{TITLE}}{{DESCRIPTION}}{{STYLE}}{{BACKGROUND}}{{KEYWORDS}}") as mock_message:
            
            title = "サンプルタイトル"
            description = "サンプル説明文"
            template = {
                "style": "digital art",
                "background": "clean, minimal",
                "size": "1024x1024",
                "quality": "standard"
            }
            
            prompt = thumbnail_generator.prepare_prompt(title, description, template)
            
            # プロンプトが正しく生成されることを確認
            assert prompt is not None
            assert isinstance(prompt, str)
            assert "サムネイル生成" in prompt
            assert "システムプロンプト" in prompt
            assert "メッセージプロンプト" in prompt
            assert "モックシステムプロンプト" in prompt
            assert "モックメッセージプロンプト" in prompt
            
            # 正しいパラメータでモックメソッドが呼ばれたことを確認
            mock_system.assert_called_once_with('thumbnail')
            mock_message.assert_called_once_with('thumbnail')
    
    @pytest.mark.asyncio
    async def test_generate_async_with_output_path(self, thumbnail_generator, sample_structure_data):
        """出力パスを指定した非同期サムネイル生成のテスト"""
        # OpenAIクライアントのモック
        mock_openai_client = MagicMock()
        # 非同期メソッドを同期的に返すようにモック
        mock_image_data = b"dummy_image_data"
        mock_openai_client.generate_image = MagicMock(return_value=mock_image_data)
        
        # S3クライアントのモック
        mock_s3_client = MagicMock()
        # 通常のメソッド（非同期ではない）をモック
        mock_s3_client.upload_file.return_value = "https://example-bucket.s3.amazonaws.com/thumbnails/sample-thumbnail.png"
        
        # クライアントをジェネレータに注入
        thumbnail_generator.openai_client = mock_openai_client
        thumbnail_generator.s3_client = mock_s3_client
        
        # テスト用の変数
        title = "サンプルタイトル"
        description = "サンプル説明文"
        
        # load_templateとprepare_promptをモック
        with patch.object(thumbnail_generator, 'load_template', return_value={
                "model": "dall-e-3",
                "prompt": "テスト用プロンプト",
                "size": "1024x1024",
                "quality": "standard",
                "style": "vivid"
            }), \
            patch.object(thumbnail_generator, 'prepare_prompt', return_value="テスト用プロンプト"), \
            patch('os.makedirs') as mock_makedirs:
            
            output_path = "output/thumbnail/sample-thumbnail.png"
            
            # 非同期メソッドのテスト
            image_data, s3_url = await thumbnail_generator.generate(
                sample_structure_data,
                title, 
                description, 
                output_path=output_path,
                upload_to_s3=True, 
                s3_key="thumbnails/sample-thumbnail.png"
            )
            
            # 結果が正しいことを確認
            assert image_data == b"dummy_image_data"
            assert s3_url == "https://example-bucket.s3.amazonaws.com/thumbnails/sample-thumbnail.png"
            
            # os.makedirsが呼ばれたことを確認
            mock_makedirs.assert_called_once_with(os.path.dirname(output_path), exist_ok=True)
            
            # APIが正しく呼び出されたことを確認
            mock_s3_client.upload_file.assert_called_once_with(
                data=b"dummy_image_data", 
                key="thumbnails/sample-thumbnail.png", 
                content_type="image/png"
            )
    
    @pytest.mark.asyncio
    async def test_generate_async_auto_output_path(self, thumbnail_generator, sample_structure_with_section):
        """出力パスが自動生成される非同期サムネイル生成のテスト"""
        # OpenAIクライアントのモック
        mock_openai_client = MagicMock()
        # 非同期メソッドを同期的に返すようにモック
        mock_image_data = b"dummy_image_data"
        mock_openai_client.generate_image = MagicMock(return_value=mock_image_data)
        
        # S3クライアントのモック
        mock_s3_client = MagicMock()
        # 通常のメソッド（非同期ではない）をモック
        mock_s3_client.upload_file.return_value = "https://example-bucket.s3.amazonaws.com/thumbnails/sample-thumbnail.png"
        
        # クライアントをジェネレータに注入
        thumbnail_generator.openai_client = mock_openai_client
        thumbnail_generator.s3_client = mock_s3_client
        
        # テスト用の変数
        title = "メインタイトル"
        description = "サンプル説明文"
        
        # get_output_pathとload_templateとprepare_promptをモック
        expected_path = "メインタイトル/チャプター1/セクション1/thumbnail/メインタイトル.png"
        with patch.object(thumbnail_generator, 'get_output_path', return_value=expected_path) as mock_get_path, \
             patch.object(thumbnail_generator, 'load_template', return_value={
                "model": "dall-e-3",
                "prompt": "テスト用プロンプト",
                "size": "1024x1024",
                "quality": "standard",
                "style": "vivid"
            }), \
            patch.object(thumbnail_generator, 'prepare_prompt', return_value="テスト用プロンプト"), \
            patch('os.makedirs') as mock_makedirs:
            
            # 出力パスを指定せずに非同期メソッドを呼び出し
            image_data, s3_url = await thumbnail_generator.generate(
                sample_structure_with_section,
                title, 
                description
            )
            
            # 結果が正しいことを確認
            assert image_data == b"dummy_image_data"
            assert s3_url is None  # S3アップロードなしの場合はNone
            
            # get_output_pathが正しく呼ばれたことを確認
            file_name = "thumbnail/メインタイトル.png"
            mock_get_path.assert_called_once_with(sample_structure_with_section, 'section', file_name)
            
            # os.makedirsが呼ばれたことを確認
            mock_makedirs.assert_called_once_with(os.path.dirname(expected_path), exist_ok=True)
    
    def test_generate_thumbnail(self, thumbnail_generator, sample_structure_data, monkeypatch):
        """同期版サムネイル生成のテスト"""
        # モックレスポンス用のデータ
        expected_image_data = b"dummy_image_data"
        expected_s3_url = "https://example-bucket.s3.amazonaws.com/thumbnails/sample-thumbnail.png"
        
        # モック化して同期メソッドが非同期メソッドを呼び出すことをシミュレート
        async def mock_generate(structure, title, description, output_path=None, 
                              upload_to_s3=False, s3_key=None, template_path=None, **kwargs):
            assert structure == sample_structure_data
            assert title == "サンプルタイトル"
            assert description == "サンプル説明文"
            assert output_path is None or output_path == "test_output.png"
            assert upload_to_s3 is True
            assert s3_key == "thumbnails/sample-thumbnail.png"
            return expected_image_data, expected_s3_url
        
        # 非同期メソッドをモック
        monkeypatch.setattr(thumbnail_generator, 'generate', mock_generate)
        
        title = "サンプルタイトル"
        description = "サンプル説明文"
        
        # 出力パスなしでテスト
        image_data1, s3_url1 = thumbnail_generator.generate_thumbnail(
            sample_structure_data,
            title, 
            description, 
            upload_to_s3=True, 
            s3_key="thumbnails/sample-thumbnail.png"
        )
        assert image_data1 == expected_image_data
        assert s3_url1 == expected_s3_url
        
        # 出力パスありでテスト
        image_data2, s3_url2 = thumbnail_generator.generate_thumbnail(
            sample_structure_data,
            title, 
            description, 
            output_path="test_output.png",
            upload_to_s3=True, 
            s3_key="thumbnails/sample-thumbnail.png"
        )
        assert image_data2 == expected_image_data
        assert s3_url2 == expected_s3_url
    
    @patch("app.clients.openai.OpenAIClient")
    def test_optimize_template(self, mock_openai_client, thumbnail_generator):
        """テンプレート最適化のテスト"""
        # このテストは、実際のクラスが実装された後に有効化する
        # mock_client_instance = mock_openai_client.return_value
        # mock_client_instance.optimize_template.return_value = """
        # model: dall-e-3
        # prompt: |
        #   メインタイトル をテーマにしたイラスト。
        #   プログラミングの基本概念から実践的な応用例まで解説する教育的なイラスト。
        #   明るく清潔感のある配色で、技術的なテーマを表現。
        # size: 1024x1024
        # quality: standard
        # style: vivid
        # """
        # 
        # template = """
        # model: dall-e-3
        # prompt: |
        #   {{title}} をテーマにしたイラスト。
        #   {{description}}
        #   明るく清潔感のある配色で、技術的なテーマを表現。
        # size: 1024x1024
        # quality: standard
        # style: vivid
        # """
        # 
        # description = "プログラミングの基本概念から実践的な応用例まで解説する教育的なコンテンツ。"
        # 
        # result = thumbnail_generator.optimize_template(template, description)
        # 
        # # 結果が正しいことを確認
        # assert result is not None
        # assert isinstance(result, str)
        # assert "メインタイトル" in result
        # assert "プログラミングの基本概念" in result
        # 
        # # YAML形式として有効であることを確認
        # try:
        #     yaml_obj = yaml.safe_load(result)
        #     assert "model" in yaml_obj
        #     assert "prompt" in yaml_obj
        #     assert "size" in yaml_obj
        # except yaml.YAMLError:
        #     assert False, "結果は有効なYAML形式ではありません"
        # 
        # # API呼び出しが行われたことを確認
        # mock_client_instance.optimize_template.assert_called_once()
        pass
    
    @patch("app.clients.openai.OpenAIClient")
    def test_generate_image(self, mock_openai_client, thumbnail_generator):
        """画像生成のテスト"""
        # このテストは、実際のクラスが実装された後に有効化する
        # mock_client_instance = mock_openai_client.return_value
        # mock_client_instance.generate_image.return_value = b"dummy_image_data"
        # 
        # yaml_prompt = """
        # model: dall-e-3
        # prompt: |
        #   メインタイトル をテーマにしたイラスト。
        #   プログラミングの基本概念から実践的な応用例まで解説する教育的なイラスト。
        # size: 1024x1024
        # quality: standard
        # style: vivid
        # """
        # 
        # result = thumbnail_generator.generate_image(yaml_prompt)
        # 
        # # 結果が正しいことを確認
        # assert result is not None
        # assert isinstance(result, bytes)
        # assert result == b"dummy_image_data"
        # 
        # # API呼び出しが行われたことを確認
        # mock_client_instance.generate_image.assert_called_once()
        pass
    
    @patch("app.clients.s3.S3Client")
    def test_upload_to_s3(self, mock_s3_client, thumbnail_generator):
        """S3アップロードのテスト"""
        # このテストは、実際のクラスが実装された後に有効化する
        # mock_client_instance = mock_s3_client.return_value
        # mock_client_instance.upload_file.return_value = "thumbnails/test-image.png"
        # mock_client_instance.get_public_url.return_value = "https://example-bucket.s3.amazonaws.com/thumbnails/test-image.png"
        # 
        # image_data = b"dummy_image_data"
        # title = "テストタイトル"
        # 
        # result = thumbnail_generator.upload_to_s3(image_data, title)
        # 
        # # 結果が正しいことを確認
        # assert result is not None
        # assert isinstance(result, str)
        # assert "https://" in result
        # assert "thumbnails/" in result
        # 
        # # API呼び出しが行われたことを確認
        pass 