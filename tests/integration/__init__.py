"""統合テストモジュール."""

import pytest
import asyncio
from typing import AsyncGenerator

# 共通のイベントループ設定
pytest_plugins = ["pytest_asyncio"] 