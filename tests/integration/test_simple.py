#!/usr/bin/env python3
"""簡単なテストスクリプト."""

import pytest
import asyncio
from src.generators.script import ScriptGenerator
from src.generators.base import GenerationRequest

# テスト用設定
class MockConfig:
    def __init__(self):
        from types import SimpleNamespace
        self.workers = SimpleNamespace()
        self.workers.max_concurrent_tasks = 5

@pytest.mark.asyncio
async def test_simple_script_generation():
    """シンプルなスクリプト生成のテスト."""
    config = MockConfig()
    generator = ScriptGenerator(config)
    request = GenerationRequest(
        title='テスト',
        content='テストコンテンツ',
        content_type='paragraph',
        lang='ja'
    )
    result = await generator.generate(request)
    print(f'Success: {result.success}')
    print(f'Content length: {len(result.content)}')
    if result.success:
        print('Test passed!')
    else:
        print(f'Error: {result.error}')
    
    # アサーションを追加
    assert result is not None
    assert hasattr(result, 'success')
    assert hasattr(result, 'content')

if __name__ == "__main__":
    asyncio.run(test_simple_script_generation()) 