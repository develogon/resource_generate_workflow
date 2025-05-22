import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート
from app.generators.script import ScriptGenerator


class TestScriptGenerator:
    """台本ジェネレータのテストクラス"""
    
    @pytest_asyncio.fixture
    async def script_generator(self):
        """テスト用の台本ジェネレータインスタンスを作成"""
        return ScriptGenerator()
    
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
    
    def test_prepare_script_prompt(self, script_generator, sample_structure_data):
        """台本生成用プロンプト準備のテスト"""
        # get_system_promptとget_message_promptをモック化
        with patch.object(script_generator, 'get_system_prompt', return_value="モックシステムプロンプト") as mock_system, \
             patch.object(script_generator, 'get_message_prompt', return_value="モックメッセージプロンプト{{ARTICLE_CONTENT}}") as mock_message:
            
            article_content = "# メインタイトル\n\nこれは記事の内容です..."
            
            prompt = script_generator.prepare_prompt(sample_structure_data, article_content)
            
            # プロンプトが正しく生成されることを確認
            assert prompt is not None
            assert isinstance(prompt, str)
            assert "台本作成" in prompt
            assert "システムプロンプト" in prompt
            assert "メッセージプロンプト" in prompt
            assert "記事タイトル" in prompt
            assert sample_structure_data["title"] in prompt
            assert "モックシステムプロンプト" in prompt
            assert "モックメッセージプロンプト" in prompt
            
            # 正しいパラメータでモックメソッドが呼ばれたことを確認
            mock_system.assert_called_once_with('script')
            mock_message.assert_called_once_with('script')
    
    @pytest.mark.asyncio
    async def test_generate_async(self, script_generator, sample_structure_data):
        """非同期台本生成のテスト"""
        # モックの非同期メソッド定義
        async def mock_call_api(request):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": """# 台本：メインタイトル

## 登場人物
- 司会者（MC）：番組の進行役
- 専門家（EXPERT）：技術の専門家

## 台本

MC: みなさんこんにちは！今回のテーマは「メインタイトル」です。

EXPERT: こんにちは。今日はこのテーマについて詳しく解説します。

MC: まず基本的なことから教えてください。

EXPERT: はい、まず最初に重要なポイントは...
"""
                    }
                ]
            }
        
        # クライアントのモック設定
        mock_client = MagicMock()
        mock_client.prepare_request.return_value = {"prompt": "テスト用プロンプト"}
        mock_client.call_api = mock_call_api
        mock_client.extract_content.return_value = """# 台本：メインタイトル

## 登場人物
- 司会者（MC）：番組の進行役
- 専門家（EXPERT）：技術の専門家

## 台本

MC: みなさんこんにちは！今回のテーマは「メインタイトル」です。

EXPERT: こんにちは。今日はこのテーマについて詳しく解説します。
"""
        # モッククライアントを注入
        script_generator.client = mock_client
        
        article_content = "# メインタイトル\n\nこれは記事の内容です..."
        
        # 非同期メソッドのテスト
        result = await script_generator.generate(sample_structure_data, article_content)
        
        # 結果が正しいことを確認
        assert result is not None
        assert isinstance(result, str)
        assert "台本：メインタイトル" in result
        assert "登場人物" in result
        assert "MC:" in result
        assert "EXPERT:" in result
        
        # API呼び出しの準備が行われたことを確認
        mock_client.prepare_request.assert_called_once()
    
    def test_generate_script(self, script_generator, sample_structure_data, monkeypatch):
        """同期版台本生成のテスト"""
        # モックレスポンス用関数
        expected_result = """# 台本：メインタイトル

## 登場人物
- 司会者（MC）：番組の進行役
- 専門家（EXPERT）：技術の専門家

## 台本

MC: みなさんこんにちは！今回のテーマは「メインタイトル」です。

EXPERT: こんにちは。今日はこのテーマについて詳しく解説します。
"""
        
        # モック化して同期メソッドが非同期メソッドを呼び出すことをシミュレート
        async def mock_generate(*args, **kwargs):
            return expected_result
        
        # 非同期メソッドをモック
        monkeypatch.setattr(script_generator, 'generate', mock_generate)
        
        article_content = "# メインタイトル\n\nこれは記事の内容です..."
        
        # 同期メソッドのテスト
        result = script_generator.generate_script(sample_structure_data, article_content)
        
        # 結果が正しいことを確認
        assert result == expected_result 