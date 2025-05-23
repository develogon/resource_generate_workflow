# Makefile for Resource Generate Workflow

.PHONY: install dev test lint format docker-build docker-run setup clean

# 環境構築
install:
	pip install -e .

dev:
	pip install -e ".[dev]"

# テスト
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

# コード品質
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

# Docker
docker-build:
	docker build -t resource-workflow .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

# セットアップ
setup: dev
	cp env.example .env
	@echo "環境変数を .env ファイルで設定してください"

# クリーンアップ
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# 実行
run:
	python -m src.cli

# ヘルプ
help:
	@echo "利用可能なコマンド:"
	@echo "  install     - パッケージのインストール"
	@echo "  dev         - 開発用依存関係のインストール"
	@echo "  test        - 全テストの実行"
	@echo "  lint        - コード検査"
	@echo "  format      - コードフォーマット"
	@echo "  setup       - 初期セットアップ"
	@echo "  clean       - 一時ファイルの削除"
	@echo "  run         - アプリケーションの実行" 