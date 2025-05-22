import pytest
import pytest_asyncio
import os
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open

# テスト対象のモジュールをインポート
from app.generators.description import DescriptionGenerator

class TestDescriptionGenerator:
    """説明文ジェネレータのテストクラス"""
    
    @pytest_asyncio.fixture
    async def description_generator(self):
        """テスト用の説明文ジェネレータインスタンスを作成"""
        return DescriptionGenerator()
    
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
    
    def test_prepare_description_prompt(self, description_generator):
        """説明文生成用プロンプト準備のテスト"""
        # get_system_promptとget_message_promptをモック化
        with patch.object(description_generator, 'get_system_prompt', return_value="モックシステムプロンプト") as mock_system, \
             patch.object(description_generator, 'get_message_prompt', return_value="モックメッセージプロンプト{{STRUCTURE_MD}}{{ARTICLE_CONTENT}}{{MIN_LENGTH}}{{MAX_LENGTH}}") as mock_message:
            
            structure_md = "# メインタイトル\n\n## 第1章: はじめに\n- 1.1 基本概念\n..."
            article_content = "# メインタイトル\n\nこれは記事の内容です..."
            
            prompt = description_generator.prepare_prompt(structure_md, article_content)
            
            # プロンプトが正しく生成されることを確認
            assert prompt is not None
            assert isinstance(prompt, str)
            assert "説明文作成" in prompt
            assert "システムプロンプト" in prompt
            assert "メッセージプロンプト" in prompt
            assert "モックシステムプロンプト" in prompt
            assert "モックメッセージプロンプト" in prompt
            
            # 正しいパラメータでモックメソッドが呼ばれたことを確認
            mock_system.assert_called_once_with('description')
            mock_message.assert_called_once_with('description')
    
    @pytest.mark.asyncio
    async def test_generate_async_with_output_path(self, description_generator, sample_structure_data):
        """出力パスを指定した非同期説明文生成のテスト"""
        # モックの非同期メソッド定義
        async def mock_call_api(request):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": """# メインタイトル - 説明文

本コンテンツでは、プログラミングの基本概念から実践的な応用例まで、体系的に学ぶことができます。

初めてプログラミングに触れる方でも理解しやすいように、基礎的な内容からステップバイステップで解説しています。
"""
                    }
                ]
            }
        
        # クライアントのモック設定
        mock_client = MagicMock()
        mock_client.prepare_request.return_value = {"prompt": "テスト用プロンプト"}
        mock_client.call_api = mock_call_api
        mock_client.extract_content.return_value = """# メインタイトル - 説明文

本コンテンツでは、プログラミングの基本概念から実践的な応用例まで、体系的に学ぶことができます。

初めてプログラミングに触れる方でも理解しやすいように、基礎的な内容からステップバイステップで解説しています。
"""
        # モッククライアントを注入
        description_generator.client = mock_client
        
        # append_templateをモック
        with patch.object(description_generator, 'append_template', return_value="""# メインタイトル - 説明文

本コンテンツでは、プログラミングの基本概念から実践的な応用例まで、体系的に学ぶことができます。

初めてプログラミングに触れる方でも理解しやすいように、基礎的な内容からステップバイステップで解説しています。

---

© 2023 サンプルプロジェクト
"""), \
             patch('os.makedirs') as mock_makedirs:
            
            structure_md = "# メインタイトル\n\n## 第1章: はじめに\n- 1.1 基本概念\n..."
            article_content = "# メインタイトル\n\nこれは記事の内容です..."
            output_path = "output/description.md"
            
            # 非同期メソッドのテスト
            result = await description_generator.generate(
                sample_structure_data, structure_md, article_content,
                min_length=300, max_length=500, output_path=output_path
            )
            
            # 結果が正しいことを確認
            assert result is not None
            assert isinstance(result, str)
            assert "メインタイトル - 説明文" in result
            assert "本コンテンツでは" in result
            assert "© 2023" in result
            
            # os.makedirsが呼ばれたことを確認
            mock_makedirs.assert_called_once_with(os.path.dirname(output_path), exist_ok=True)
            
            # API呼び出しが行われたことを確認
            mock_client.prepare_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_async_auto_output_path(self, description_generator, sample_structure_with_section):
        """出力パスが自動生成される非同期説明文生成のテスト"""
        # モックの非同期メソッド定義
        async def mock_call_api(request):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": """# メインタイトル - 説明文

本コンテンツでは、プログラミングの基本概念から実践的な応用例まで、体系的に学ぶことができます。
"""
                    }
                ]
            }
        
        # クライアントのモック設定
        mock_client = MagicMock()
        mock_client.prepare_request.return_value = {"prompt": "テスト用プロンプト"}
        mock_client.call_api = mock_call_api
        mock_client.extract_content.return_value = """# メインタイトル - 説明文

本コンテンツでは、プログラミングの基本概念から実践的な応用例まで、体系的に学ぶことができます。
"""
        # モッククライアントを注入
        description_generator.client = mock_client
        
        # append_templateとget_output_pathをモック
        expected_path = "メインタイトル/チャプター1/セクション1/description.md"
        with patch.object(description_generator, 'append_template', return_value="モック説明文") as mock_append, \
             patch.object(description_generator, 'get_output_path', return_value=expected_path) as mock_get_path, \
             patch('os.makedirs') as mock_makedirs:
            
            structure_md = "# メインタイトル\n\n## 第1章: はじめに\n- 1.1 基本概念\n..."
            article_content = "# メインタイトル\n\nこれは記事の内容です..."
            
            # 出力パスを指定せずに非同期メソッドを呼び出し
            result = await description_generator.generate(
                sample_structure_with_section, structure_md, article_content
            )
            
            # 結果が正しいことを確認
            assert result is not None
            assert isinstance(result, str)
            assert result == "モック説明文"
            
            # get_output_pathが正しく呼ばれたことを確認
            mock_get_path.assert_called_once_with(sample_structure_with_section, 'section', 'description.md')
            
            # os.makedirsが呼ばれたことを確認
            mock_makedirs.assert_called_once_with(os.path.dirname(expected_path), exist_ok=True)
    
    def test_generate_description(self, description_generator, sample_structure_data, monkeypatch):
        """同期版説明文生成のテスト"""
        # モックレスポンス用の文字列
        expected_result = """# メインタイトル - 説明文

本コンテンツでは、プログラミングの基本概念から実践的な応用例まで、体系的に学ぶことができます。

初めてプログラミングに触れる方でも理解しやすいように、基礎的な内容からステップバイステップで解説しています。

---

© 2023 サンプルプロジェクト
"""
        
        # モック化して同期メソッドが非同期メソッドを呼び出すことをシミュレート
        async def mock_generate(structure, structure_md, article_content, min_length=300, max_length=500, 
                               output_path=None, append_footer=True):
            assert structure == sample_structure_data
            assert "メインタイトル" in structure_md
            assert "記事の内容" in article_content
            assert min_length == 300
            assert max_length == 500
            assert output_path is None or output_path == "test_output.md"
            assert append_footer is True
            return expected_result
        
        # 非同期メソッドをモック
        monkeypatch.setattr(description_generator, 'generate', mock_generate)
        
        structure_md = "# メインタイトル\n\n## 第1章: はじめに\n- 1.1 基本概念\n..."
        article_content = "# メインタイトル\n\nこれは記事の内容です..."
        
        # 出力パスなしでテスト
        result1 = description_generator.generate_description(
            sample_structure_data, structure_md, article_content
        )
        assert result1 == expected_result
        
        # 出力パスありでテスト
        result2 = description_generator.generate_description(
            sample_structure_data, structure_md, article_content, 
            min_length=300, max_length=500, output_path="test_output.md"
        )
        assert result2 == expected_result
    
    @patch("builtins.open", new_callable=mock_open, read_data="# テンプレート\n\n著作権表示: {{year}} 著作者名")
    def test_append_template(self, mock_file, description_generator):
        """テンプレート追記のテスト"""
        # open関数のモックで、ファイルパスを検証
        with patch('os.path.join', return_value='/mock/path/templates/description/footer.txt'):
            description = "# メインタイトル - 説明文\n\n本コンテンツの説明文です。"
            
            # 現在の年を取得
            current_year = datetime.now().year
            
            # テンプレート追記
            result = description_generator.append_template(description)
            
            # 結果が正しいことを確認
            assert result is not None
            assert isinstance(result, str)
            assert description in result
            assert "# テンプレート" in result
            assert f"著作権表示: {current_year} 著作者名" in result
            
            # ファイルが読み込まれたことを確認
            mock_file.assert_called_once_with('/mock/path/templates/description/footer.txt', 'r', encoding='utf-8') 