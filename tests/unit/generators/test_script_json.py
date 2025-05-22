import pytest
import pytest_asyncio
import json
import os
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
    async def test_generate_async_with_output_path(self, script_json_generator, sample_structure_data):
        """出力パスを指定した非同期台本JSON生成のテスト"""
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
        
        # os.makedirsをモック化
        with patch('os.makedirs') as mock_makedirs:
            # 出力パスを指定
            output_path = "output/script.json"
            
            # 非同期メソッドのテスト
            result = await script_json_generator.generate(sample_structure_data, script_content, output_path)
            
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
            
            # os.makedirsが呼ばれたことを確認
            mock_makedirs.assert_called_once_with(os.path.dirname(output_path), exist_ok=True)
            
            # API呼び出しが行われたことを確認
            mock_client.prepare_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_async_auto_output_path(self, script_json_generator, sample_structure_with_section):
        """出力パスが自動生成される非同期台本JSON生成のテスト"""
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
        
        # get_output_pathとos.makedirsをモック化
        expected_path = "メインタイトル/チャプター1/セクション1/script.json"
        with patch.object(script_json_generator, 'get_output_path', return_value=expected_path) as mock_get_path, \
             patch('os.makedirs') as mock_makedirs:
            
            # 出力パスを指定せずに非同期メソッドを呼び出し
            result = await script_json_generator.generate(sample_structure_with_section, script_content)
            
            # 結果が正しいことを確認
            assert result is not None
            assert isinstance(result, str)
            
            # get_output_pathが正しく呼ばれたことを確認
            mock_get_path.assert_called_once_with(sample_structure_with_section, 'section', 'script.json')
            
            # os.makedirsが呼ばれたことを確認
            mock_makedirs.assert_called_once_with(os.path.dirname(expected_path), exist_ok=True)
    
    @pytest.mark.asyncio
    async def test_generate_async_with_error(self, script_json_generator, sample_structure_data):
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
            await script_json_generator.generate(sample_structure_data, script_content)
        
        assert "APIレスポンスからコンテンツを抽出できませんでした" in str(excinfo.value)
    
    def test_generate_script_json(self, script_json_generator, sample_structure_data, monkeypatch):
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
        async def mock_generate(structure, script_content, output_path=None):
            assert structure == sample_structure_data
            assert "登場人物" in script_content
            assert output_path is None or output_path == "test_output.json"
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
        
        # 出力パスなしでテスト
        result1 = script_json_generator.generate_script_json(sample_structure_data, script_content)
        assert result1 == expected_result
        
        # 出力パスありでテスト
        result2 = script_json_generator.generate_script_json(sample_structure_data, script_content, "test_output.json")
        assert result2 == expected_result
    
    def test_generate_script_json_with_error(self, script_json_generator, sample_structure_data, monkeypatch):
        """エラー発生時の同期版台本JSON生成のテスト"""
        # エラーを発生させる非同期メソッドをモック
        async def mock_generate_error(structure, script_content, output_path=None):
            raise ValueError("テストエラー")
        
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
            script_json_generator.generate_script_json(sample_structure_data, script_content)
        
        assert "テストエラー" in str(excinfo.value) 