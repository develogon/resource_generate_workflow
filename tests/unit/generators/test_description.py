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
    async def test_generate_async(self, description_generator):
        """非同期説明文生成のテスト"""
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
"""):
            structure_md = "# メインタイトル\n\n## 第1章: はじめに\n- 1.1 基本概念\n..."
            article_content = "# メインタイトル\n\nこれは記事の内容です..."
            
            # 非同期メソッドのテスト
            result = await description_generator.generate(structure_md, article_content)
            
            # 結果が正しいことを確認
            assert result is not None
            assert isinstance(result, str)
            assert "メインタイトル - 説明文" in result
            assert "本コンテンツでは" in result
            assert "© 2023" in result
            
            # API呼び出しが行われたことを確認
            mock_client.prepare_request.assert_called_once()
    
    def test_generate_description(self, description_generator, monkeypatch):
        """同期版説明文生成のテスト"""
        # モックレスポンス用の文字列
        expected_result = """# メインタイトル - 説明文

本コンテンツでは、プログラミングの基本概念から実践的な応用例まで、体系的に学ぶことができます。

初めてプログラミングに触れる方でも理解しやすいように、基礎的な内容からステップバイステップで解説しています。

---

© 2023 サンプルプロジェクト
"""
        
        # モック化して同期メソッドが非同期メソッドを呼び出すことをシミュレート
        async def mock_generate(*args, **kwargs):
            return expected_result
        
        # 非同期メソッドをモック
        monkeypatch.setattr(description_generator, 'generate', mock_generate)
        
        structure_md = "# メインタイトル\n\n## 第1章: はじめに\n- 1.1 基本概念\n..."
        article_content = "# メインタイトル\n\nこれは記事の内容です..."
        
        # 同期メソッドのテスト
        result = description_generator.generate_description(structure_md, article_content)
        
        # 結果が正しいことを確認
        assert result == expected_result
    
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