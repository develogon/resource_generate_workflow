#!/usr/bin/env python3
"""簡単なテストスクリプト."""

import sys
sys.path.insert(0, '../../src')
import asyncio
from generators.script import ScriptGenerator
from generators.base import GenerationRequest

# テスト用設定
class TestConfig:
    def __init__(self):
        from types import SimpleNamespace
        self.workers = SimpleNamespace()
        self.workers.max_concurrent_tasks = 5

async def test():
    config = TestConfig()
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

if __name__ == "__main__":
    asyncio.run(test()) 