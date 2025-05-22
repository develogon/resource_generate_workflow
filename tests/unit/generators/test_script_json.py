import pytest
import pytest_asyncio
import json
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート
from app.generators.script_json import ScriptJsonGenerator

class TestScriptJsonGenerator:
    """台本JSONジェネレータのテストクラス"""
    
    @pytest_asyncio.fixture
    async def script_json_generator(self):
        """テスト用の台本JSONジェネレータインスタンスを作成"""
        return ScriptJsonGenerator()
    
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
    
    def test_prepare_script_json_prompt(self, script_json_generator, sample_structure_data):
        """台本JSON生成用プロンプト準備のテスト"""
        # get_system_promptとget_message_promptをモック化
        with patch.object(script_json_generator, 'get_system_prompt', return_value="モックシステムプロンプト") as mock_system, \
             patch.object(script_json_generator, 'get_message_prompt', return_value="モックメッセージプロンプト{{SCRIPT_CONTENT}}") as mock_message:
            
            script_content = "# 台本：メインタイトル\n\n..."
            
            prompt = script_json_generator.prepare_prompt(script_content)
            
            # プロンプトが正しく生成されることを確認
            assert prompt is not None
            assert isinstance(prompt, str)
            assert "台本のJSON変換" in prompt
            assert "システムプロンプト" in prompt
            assert "メッセージプロンプト" in prompt
            assert "モックシステムプロンプト" in prompt
            assert "モックメッセージプロンプト" in prompt
            
            # 正しいパラメータでモックメソッドが呼ばれたことを確認
            mock_system.assert_called_once_with('script_json')
            mock_message.assert_called_once_with('script_json')
    
    def test_process_response_with_empty_content(self, script_json_generator):
        """空のコンテンツを処理する場合のテスト"""
        # モッククライアントを設定
        mock_client = MagicMock()
        mock_client.extract_content.return_value = ""
        script_json_generator.client = mock_client
        
        # 空のコンテンツを処理するとValueErrorが発生することを確認
        with pytest.raises(ValueError) as excinfo:
            script_json_generator.process_response({})
        
        assert "APIレスポンスからコンテンツを抽出できませんでした" in str(excinfo.value)
    
    def test_process_response_with_invalid_json(self, script_json_generator):
        """無効なJSON形式のコンテンツを処理する場合のテスト"""
        # モッククライアントを設定
        mock_client = MagicMock()
        mock_client.extract_content.return_value = "これはJSONではありません"
        script_json_generator.client = mock_client
        
        # 無効なJSON形式のコンテンツを処理するとValueErrorが発生することを確認
        with pytest.raises(ValueError) as excinfo:
            script_json_generator.process_response({})
        
        assert "レスポンスからJSON形式を抽出できませんでした" in str(excinfo.value)
    
    def test_process_response_with_invalid_json_format(self, script_json_generator):
        """JSONパース不可能なコンテンツを処理する場合のテスト"""
        # モッククライアントを設定
        mock_client = MagicMock()
        mock_client.extract_content.return_value = "```json\n{\"title\": \"不正なJSON\", \"missing\": }\n```"
        script_json_generator.client = mock_client
        
        # JSONパース不可能なコンテンツを処理するとValueErrorが発生することを確認
        with pytest.raises(ValueError) as excinfo:
            script_json_generator.process_response({})
        
        assert "JSON解析エラー" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_generate_async(self, script_json_generator):
        """非同期台本JSON生成のテスト"""
        # モックの非同期メソッド定義
        async def mock_call_api(request):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": """```json
{
  "title": "メインタイトル",
  "characters": [
    {"name": "MC", "display_name": "司会者", "description": "番組の進行役"},
    {"name": "EXPERT", "display_name": "専門家", "description": "技術の専門家"}
  ],
  "script": [
    {"type": "dialog", "speaker": "MC", "line": "みなさんこんにちは！今回のテーマは「メインタイトル」です。"},
    {"type": "dialog", "speaker": "EXPERT", "line": "こんにちは。今日はこのテーマについて詳しく解説します。"}
  ]
}
```"""
                    }
                ]
            }
        
        # クライアントのモック設定
        mock_client = MagicMock()
        mock_client.prepare_request.return_value = {"prompt": "テスト用プロンプト"}
        mock_client.call_api = mock_call_api
        mock_client.extract_content.return_value = """```json
{
  "title": "メインタイトル",
  "characters": [
    {"name": "MC", "display_name": "司会者", "description": "番組の進行役"},
    {"name": "EXPERT", "display_name": "専門家", "description": "技術の専門家"}
  ],
  "script": [
    {"type": "dialog", "speaker": "MC", "line": "みなさんこんにちは！今回のテーマは「メインタイトル」です。"},
    {"type": "dialog", "speaker": "EXPERT", "line": "こんにちは。今日はこのテーマについて詳しく解説します。"}
  ]
}
```"""
        # モッククライアントを注入
        script_json_generator.client = mock_client
        
        script_content = """# 台本：メインタイトル

## 登場人物
- 司会者（MC）：番組の進行役
- 専門家（EXPERT）：技術の専門家

## 台本

MC: みなさんこんにちは！今回のテーマは「メインタイトル」です。

EXPERT: こんにちは。今日はこのテーマについて詳しく解説します。
"""
        
        # 非同期メソッドのテスト
        result = await script_json_generator.generate(script_content)
        
        # 結果が正しいことを確認
        assert result is not None
        assert isinstance(result, str)
        
        # JSON形式であることを確認
        try:
            json_obj = json.loads(result)
            assert "title" in json_obj
            assert "characters" in json_obj
            assert "script" in json_obj
            assert len(json_obj["characters"]) == 2
            assert len(json_obj["script"]) == 2
            assert json_obj["characters"][0]["name"] == "MC"
            assert json_obj["characters"][1]["name"] == "EXPERT"
        except json.JSONDecodeError:
            assert False, "結果は有効なJSON形式ではありません"
        
        # API呼び出しが行われたことを確認
        mock_client.prepare_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_async_with_error(self, script_json_generator):
        """APIエラー時の非同期台本JSON生成のテスト"""
        # モックの非同期メソッド定義
        async def mock_call_api(request):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": ""
                    }
                ]
            }
        
        # クライアントのモック設定
        mock_client = MagicMock()
        mock_client.prepare_request.return_value = {"prompt": "テスト用プロンプト"}
        mock_client.call_api = mock_call_api
        mock_client.extract_content.return_value = ""
        
        # モッククライアントを注入
        script_json_generator.client = mock_client
        
        script_content = """# 台本：メインタイトル

## 登場人物
- 司会者（MC）：番組の進行役
- 専門家（EXPERT）：技術の専門家

## 台本

MC: みなさんこんにちは！今回のテーマは「メインタイトル」です。

EXPERT: こんにちは。今日はこのテーマについて詳しく解説します。
"""
        
        # エラーが発生することを確認
        with pytest.raises(ValueError) as excinfo:
            await script_json_generator.generate(script_content)
        
        assert "APIレスポンスからコンテンツを抽出できませんでした" in str(excinfo.value)
    
    def test_generate_script_json(self, script_json_generator, monkeypatch):
        """同期版台本JSON生成のテスト"""
        # モックレスポンス用のJSON文字列
        expected_result = json.dumps({
            "title": "メインタイトル",
            "characters": [
                {"name": "MC", "display_name": "司会者", "description": "番組の進行役"},
                {"name": "EXPERT", "display_name": "専門家", "description": "技術の専門家"}
            ],
            "script": [
                {"type": "dialog", "speaker": "MC", "line": "みなさんこんにちは！今回のテーマは「メインタイトル」です。"},
                {"type": "dialog", "speaker": "EXPERT", "line": "こんにちは。今日はこのテーマについて詳しく解説します。"}
            ]
        }, ensure_ascii=False, indent=2)
        
        # モック化して同期メソッドが非同期メソッドを呼び出すことをシミュレート
        async def mock_generate(*args, **kwargs):
            return expected_result
        
        # 非同期メソッドをモック
        monkeypatch.setattr(script_json_generator, 'generate', mock_generate)
        
        script_content = """# 台本：メインタイトル

## 登場人物
- 司会者（MC）：番組の進行役
- 専門家（EXPERT）：技術の専門家

## 台本

MC: みなさんこんにちは！今回のテーマは「メインタイトル」です。

EXPERT: こんにちは。今日はこのテーマについて詳しく解説します。
"""
        
        # 同期メソッドのテスト
        result = script_json_generator.generate_script_json(script_content)
        
        # 結果が正しいことを確認
        assert result == expected_result
        
        # JSON形式であることを確認
        try:
            json_obj = json.loads(result)
            assert "title" in json_obj
            assert "characters" in json_obj
            assert "script" in json_obj
        except json.JSONDecodeError:
            assert False, "結果は有効なJSON形式ではありません"
    
    def test_generate_script_json_with_error(self, script_json_generator, monkeypatch):
        """エラー発生時の同期版台本JSON生成のテスト"""
        # エラーを発生させる非同期メソッド
        async def mock_generate_error(*args, **kwargs):
            raise ValueError("APIレスポンスからコンテンツを抽出できませんでした")
        
        # 非同期メソッドをモック
        monkeypatch.setattr(script_json_generator, 'generate', mock_generate_error)
        
        script_content = """# 台本：メインタイトル

## 登場人物
- 司会者（MC）：番組の進行役
- 専門家（EXPERT）：技術の専門家

## 台本

MC: みなさんこんにちは！今回のテーマは「メインタイトル」です。

EXPERT: こんにちは。今日はこのテーマについて詳しく解説します。
"""
        
        # エラーが発生することを確認
        with pytest.raises(ValueError) as excinfo:
            script_json_generator.generate_script_json(script_content)
        
        assert "APIレスポンスからコンテンツを抽出できませんでした" in str(excinfo.value) 