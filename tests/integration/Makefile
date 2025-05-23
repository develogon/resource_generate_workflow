# 統合テスト実行用Makefile

.PHONY: test test-full test-workflow test-events test-ai-media test-state test-performance clean setup help

# デフォルトターゲット
help:
	@echo "統合テスト実行用Makefile"
	@echo ""
	@echo "利用可能なターゲット:"
	@echo "  test              - 全ての統合テストを実行"
	@echo "  test-full         - 詳細なレポート付きで全テストを実行"
	@echo "  test-workflow     - ワークフロー統合テストのみ実行"
	@echo "  test-events       - イベント・ワーカー統合テストのみ実行"
	@echo "  test-ai-media     - AI・メディア統合テストのみ実行"
	@echo "  test-state        - 状態管理・復旧テストのみ実行"
	@echo "  test-performance  - パフォーマンステストのみ実行"
	@echo "  setup             - テスト環境のセットアップ"
	@echo "  clean             - テスト結果をクリーンアップ"

# 環境変数
PYTHON := python3
PYTEST := pytest
TEST_DIR := .
PROJECT_ROOT := ../..
SRC_DIR := $(PROJECT_ROOT)/src

# 基本的な統合テスト実行
test:
	@echo "統合テストを実行中..."
	PYTHONPATH=$(SRC_DIR) $(PYTEST) $(TEST_DIR) -v

# 詳細なレポート付きテスト実行
test-full:
	@echo "詳細レポート付きで統合テストを実行中..."
	PYTHONPATH=$(SRC_DIR) $(PYTEST) $(TEST_DIR) \
		-v \
		--tb=long \
		--log-cli-level=INFO \
		--cov=$(SRC_DIR) \
		--cov-report=html:htmlcov/integration \
		--cov-report=term-missing \
		--cov-report=xml:coverage-integration.xml \
		--junit-xml=junit-integration.xml

# ワークフロー統合テストのみ
test-workflow:
	@echo "ワークフロー統合テストを実行中..."
	PYTHONPATH=$(SRC_DIR) $(PYTEST) test_workflow_integration.py -v

# イベント・ワーカー統合テストのみ
test-events:
	@echo "イベント・ワーカー統合テストを実行中..."
	PYTHONPATH=$(SRC_DIR) $(PYTEST) test_event_worker_integration.py -v

# AI・メディア統合テストのみ
test-ai-media:
	@echo "AI・メディア統合テストを実行中..."
	PYTHONPATH=$(SRC_DIR) $(PYTEST) test_ai_media_integration.py -v

# 状態管理・復旧テストのみ
test-state:
	@echo "状態管理・復旧テストを実行中..."
	PYTHONPATH=$(SRC_DIR) $(PYTEST) test_state_recovery_integration.py -v

# パフォーマンステストのみ
test-performance:
	@echo "パフォーマンステストを実行中..."
	PYTHONPATH=$(SRC_DIR) $(PYTEST) test_performance_integration.py -v -m performance

# テスト環境のセットアップ
setup:
	@echo "テスト環境をセットアップ中..."
	@# Redis サーバーの起動確認
	@if ! redis-cli ping > /dev/null 2>&1; then \
		echo "警告: Redisサーバーが起動していません。"; \
		echo "統合テストを実行するには以下のコマンドでRedisを起動してください:"; \
		echo "  redis-server"; \
	else \
		echo "Redis サーバーが正常に動作しています。"; \
	fi
	@# Python依存関係の確認
	@echo "Python依存関係を確認中..."
	@pip list | grep -E "(pytest|asyncio|aioredis|psutil)" || \
		(echo "必要な依存関係をインストールしてください: pip install -r requirements/test.txt")

# テスト結果のクリーンアップ
clean:
	@echo "テスト結果をクリーンアップ中..."
	@rm -rf htmlcov/
	@rm -rf .pytest_cache/
	@rm -rf __pycache__/
	@rm -f coverage-integration.xml
	@rm -f junit-integration.xml
	@rm -f .coverage
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "クリーンアップ完了"

# CI/CD用のテスト実行
test-ci:
	@echo "CI/CD環境での統合テストを実行中..."
	PYTHONPATH=$(SRC_DIR) $(PYTEST) $(TEST_DIR) \
		-v \
		--tb=short \
		--strict-markers \
		--cov=$(SRC_DIR) \
		--cov-report=xml:coverage-integration.xml \
		--junit-xml=junit-integration.xml \
		--timeout=300 \
		-m "not slow"

# パフォーマンステストを除外したクイックテスト
test-quick:
	@echo "クイック統合テストを実行中..."
	PYTHONPATH=$(SRC_DIR) $(PYTEST) $(TEST_DIR) \
		-v \
		-m "not performance and not slow" \
		--timeout=60 