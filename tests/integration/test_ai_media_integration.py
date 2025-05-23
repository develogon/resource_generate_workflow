"""AI生成とメディア処理の統合テスト."""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock, MagicMock
import json
import sys

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# 実装されているモジュールのみインポート
from generators.base import GenerationType, GenerationRequest, GenerationResult
from generators.script import ScriptGenerator


class TestAIMediaIntegration:
    """AI生成とメディア処理の統合テストクラス."""
    
    @pytest.mark.asyncio
    async def test_script_generation_basic(
        self,
        test_config
    ):
        """基本的な台本生成テスト."""
        # 台本生成器の設定
        script_generator = ScriptGenerator(test_config)
        
        # 台本生成リクエスト
        request = GenerationRequest(
            title="Pythonプログラミング入門",
            content="Pythonの基本的な使い方を学びます。変数、関数、クラスについて説明します。",
            content_type="paragraph",
            lang="ja",
            options={
                "duration": "3:00",
                "style": "educational"
            }
        )
        
        # 台本生成
        result = await script_generator.generate(request)
        
        # 台本生成が成功したことを確認
        assert result.success
        assert result.content is not None
        assert len(result.content) > 0
        
        # 台本のJSON構造を確認
        try:
            script_data = json.loads(result.content)
            assert "title" in script_data
            assert "sections" in script_data
            assert len(script_data["sections"]) > 0
        except json.JSONDecodeError:
            # JSONでない場合もコンテンツがあれば成功とする
            assert len(result.content) > 100
    
    @pytest.mark.asyncio
    async def test_multiple_script_generation(
        self,
        test_config
    ):
        """複数台本の生成テスト."""
        script_generator = ScriptGenerator(test_config)
        
        # 複数のリクエスト
        requests = [
            GenerationRequest(
                title="Python基礎1",
                content="Pythonの変数について",
                content_type="paragraph",
                lang="ja"
            ),
            GenerationRequest(
                title="Python基礎2",
                content="Pythonの関数について",
                content_type="paragraph", 
                lang="ja"
            ),
            GenerationRequest(
                title="Python基礎3",
                content="Pythonのクラスについて",
                content_type="paragraph",
                lang="ja"
            )
        ]
        
        # バッチ生成
        results = await script_generator.batch_generate(requests)
        
        # 全ての生成が成功したことを確認
        assert len(results) == 3
        for result in results:
            assert result.success
            assert result.content is not None
            assert len(result.content) > 0
            
        # 各台本の内容を確認
        for i, result in enumerate(results):
            assert result.generation_type == GenerationType.SCRIPT
            
            # 基本的なメタデータの存在確認
            assert "generation_type" in result.metadata
            assert "source_title" in result.metadata
            assert "generated_at" in result.metadata
    
    @pytest.mark.asyncio
    async def test_script_generation_with_ai_simulation(
        self,
        test_config
    ):
        """AI生成シミュレーションのテスト."""
        script_generator = ScriptGenerator(test_config)
        
        # AIクライアントなしでの生成（シミュレーション使用）
        request = GenerationRequest(
            title="JavaScript入門",
            content="JavaScriptの基本構文とDOM操作について学びます。",
            content_type="paragraph",
            lang="ja",
            options={
                "title": "JavaScript入門",
                "duration": "2:30"
            }
        )
        
        result = await script_generator.generate(request)
        
        assert result.success
        assert result.content is not None
        
        # 台本の基本構造確認
        try:
            script_data = json.loads(result.content)
            
            # 基本フィールドの存在確認
            assert "title" in script_data
            assert "duration" in script_data
            assert "sections" in script_data
            
            # セクションの構造確認
            sections = script_data["sections"]
            assert len(sections) > 0
            
            for section in sections:
                assert "type" in section
                assert "duration" in section
                assert "script" in section
                assert "notes" in section
                
        except json.JSONDecodeError:
            # JSON形式でない場合は、コンテンツの長さで判定
            assert len(result.content) > 200
    
    @pytest.mark.asyncio
    async def test_script_generation_error_handling(
        self,
        test_config
    ):
        """台本生成のエラーハンドリングテスト."""
        script_generator = ScriptGenerator(test_config)
        
        # 無効なリクエスト（空のコンテンツ）
        invalid_request = GenerationRequest(
            title="空のテスト",
            content="",  # 空のコンテンツ
            content_type="paragraph",
            lang="ja"
        )
        
        result = await script_generator.generate(invalid_request)
        
        # エラーハンドリングの確認
        assert result.success is False
        assert result.error is not None
        assert "Invalid request" in result.error
    
    @pytest.mark.asyncio
    async def test_script_metadata_analysis(
        self,
        test_config
    ):
        """台本メタデータ分析のテスト."""
        script_generator = ScriptGenerator(test_config)
        
        request = GenerationRequest(
            title="React入門",
            content="Reactの基本概念とコンポーネントの作成について学びます。",
            content_type="paragraph",
            lang="ja",
            options={"title": "React入門"}
        )
        
        result = await script_generator.generate(request)
        
        assert result.success
        
        # メタデータの詳細確認
        metadata = result.metadata
        
        # 基本メタデータ
        assert "generation_type" in metadata
        assert metadata["generation_type"] == "script"
        assert "source_title" in metadata
        assert "generated_at" in metadata
        
        # 台本固有のメタデータ（内容に依存）
        # JSON形式の場合のみチェック
        try:
            script_data = json.loads(result.content)
            if "script_title" in metadata:
                assert isinstance(metadata["script_title"], str)
            if "section_count" in metadata:
                assert isinstance(metadata["section_count"], int)
                
        except json.JSONDecodeError:
            # JSON形式でない場合はスキップ
            pass
    
    @pytest.mark.asyncio
    async def test_concurrent_script_generation(
        self,
        test_config
    ):
        """並行台本生成のテスト."""
        script_generator = ScriptGenerator(test_config)
        
        # 並行生成用のリクエスト
        requests = [
            GenerationRequest(
                title=f"並行生成テスト{i}",
                content=f"並行生成テスト用のコンテンツ{i}です。",
                content_type="paragraph",
                lang="ja"
            )
            for i in range(1, 6)
        ]
        
        # 並行実行
        start_time = asyncio.get_event_loop().time()
        
        # asyncio.gatherを使用した並行実行
        tasks = [script_generator.generate(req) for req in requests]
        results = await asyncio.gather(*tasks)
        
        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time
        
        # 結果の確認
        assert len(results) == 5
        successful_results = [r for r in results if r.success]
        assert len(successful_results) >= 4  # 80%以上成功
        
        # 並行実行の効果確認（順次実行より高速であることを期待）
        print(f"並行実行時間: {execution_time:.2f}秒")
        assert execution_time <= 3.0  # 3秒以内での完了を期待 