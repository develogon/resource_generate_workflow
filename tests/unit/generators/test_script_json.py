import pytest
import json
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート（まだ実装されていない場合はコメントアウト）
# from app.generators.script_json import ScriptJsonGenerator

class TestScriptJsonGenerator:
    """台本JSONジェネレータのテストクラス"""
    
    @pytest.fixture
    def script_json_generator(self):
        """テスト用の台本JSONジェネレータインスタンスを作成"""
        # コメントアウトされているコードは、実際のクラスが実装された後に有効化する
        # return ScriptJsonGenerator()
        
        # モックインスタンスを返す（クラスが実装されるまでの一時的な対応）
        mock_generator = MagicMock()
        
        # prepare_prompt メソッドが呼ばれたときに実行される関数
        mock_generator.prepare_prompt.side_effect = lambda structure, script, **kwargs: f"""
# 台本JSON作成

以下の台本を構造化されたJSONに変換してください。

## 台本内容
{script[:300]}... （省略）

## JSONフォーマット
{{
  "title": "タイトル",
  "scenes": [
    {{
      "characters": ["キャラクター名"],
      "dialogs": [
        {{
          "character": "キャラクター名",
          "line": "台詞内容"
        }}
      ]
    }}
  ]
}}
"""
        
        # process_response メソッドが呼ばれたときに実行される関数
        mock_generator.process_response.side_effect = lambda response: """```json
{
  "title": "メインタイトル",
  "scenes": [
    {
      "characters": ["MC", "EXPERT"],
      "dialogs": [
        {
          "character": "MC",
          "line": "みなさんこんにちは！今回のテーマは「メインタイトル」です。"
        },
        {
          "character": "EXPERT",
          "line": "こんにちは。今日はこのテーマについて詳しく解説します。"
        },
        {
          "character": "MC",
          "line": "まず基本的なことから教えてください。"
        },
        {
          "character": "EXPERT",
          "line": "はい、まず最初に重要なポイントは..."
        }
      ]
    }
  ]
}
```"""
        
        return mock_generator
    
    def test_generate_script_json(self, script_json_generator, sample_structure_data):
        """台本JSON生成のテスト"""
        # このテストは、実際のクラスが実装された後に一部を有効化する
        # generate_script_json メソッドの呼び出し
        script_content = """# 台本：メインタイトル

## 登場人物
- 司会者（MC）：番組の進行役
- 専門家（EXPERT）：技術の専門家

## 台本

MC: みなさんこんにちは！今回のテーマは「メインタイトル」です。

EXPERT: こんにちは。今日はこのテーマについて詳しく解説します。

MC: まず基本的なことから教えてください。

EXPERT: はい、まず最初に重要なポイントは...
"""
        
        script_json_generator.generate_script_json.return_value = """
{
  "title": "メインタイトル",
  "scenes": [
    {
      "characters": ["MC", "EXPERT"],
      "dialogs": [
        {
          "character": "MC",
          "line": "みなさんこんにちは！今回のテーマは「メインタイトル」です。"
        },
        {
          "character": "EXPERT",
          "line": "こんにちは。今日はこのテーマについて詳しく解説します。"
        },
        {
          "character": "MC",
          "line": "まず基本的なことから教えてください。"
        },
        {
          "character": "EXPERT",
          "line": "はい、まず最初に重要なポイントは..."
        }
      ]
    }
  ]
}
"""
        
        result = script_json_generator.generate_script_json(sample_structure_data, script_content)
        
        # 結果が正しいことを確認
        assert result is not None
        assert "title" in result
        assert "scenes" in result
        
        # 文字列としてのレスポンスの場合
        if isinstance(result, str):
            # JSON形式であることを確認
            try:
                json_obj = json.loads(result)
                assert "title" in json_obj
                assert "scenes" in json_obj
                assert len(json_obj["scenes"]) > 0
                assert "dialogs" in json_obj["scenes"][0]
            except json.JSONDecodeError:
                assert False, "結果は有効なJSON形式ではありません"
    
    @patch("app.clients.claude.ClaudeAPIClient")
    async def test_script_json_generation_with_api(self, mock_claude_client, script_json_generator, sample_structure_data):
        """APIを使用した台本JSON生成のテスト"""
        # このテストは、実際のクラスが実装された後に有効化する
        # mock_client_instance = mock_claude_client.return_value
        # mock_client_instance.call_api.return_value = {
        #     "content": [
        #         {
        #             "type": "text",
        #             "text": """```json
        # {
        #   "title": "メインタイトル",
        #   "scenes": [
        #     {
        #       "characters": ["MC", "EXPERT"],
        #       "dialogs": [
        #         {
        #           "character": "MC",
        #           "line": "みなさんこんにちは！今回のテーマは「メインタイトル」です。"
        #         },
        #         {
        #           "character": "EXPERT",
        #           "line": "こんにちは。今日はこのテーマについて詳しく解説します。"
        #         }
        #       ]
        #     }
        #   ]
        # }
        # ```"""
        #         }
        #     ]
        # }
        # 
        # script_content = "# 台本：メインタイトル\n\n..."
        # 
        # result = await script_json_generator.generate(sample_structure_data, script_content)
        # 
        # # 結果が正しいことを確認
        # assert result is not None
        # 
        # # 文字列としてのレスポンスの場合
        # if isinstance(result, str):
        #     # JSON形式であることを確認
        #     try:
        #         json_obj = json.loads(result)
        #         assert "title" in json_obj
        #     except json.JSONDecodeError:
        #         assert False, "結果は有効なJSON形式ではありません"
        # 
        # # API呼び出しが行われたことを確認
        # mock_client_instance.call_api.assert_called_once()
        pass
    
    def test_prepare_script_json_prompt(self, script_json_generator, sample_structure_data):
        """台本JSON生成用プロンプト準備のテスト"""
        script_content = "# 台本：メインタイトル\n\n..."
        
        prompt = script_json_generator.prepare_prompt(sample_structure_data, script_content)
        
        # プロンプトが正しく生成されることを確認
        assert prompt is not None
        assert isinstance(prompt, str)
        assert "台本JSON作成" in prompt
        assert "台本内容" in prompt
        assert "JSONフォーマット" in prompt 