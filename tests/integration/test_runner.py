"""統合テスト実行用のテストランナー."""

import pytest
import sys
import os
from pathlib import Path

# プロジェクトルートを設定
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

def run_integration_tests():
    """統合テストを実行."""
    # テスト実行設定
    pytest_args = [
        # 統合テストディレクトリ
        str(Path(__file__).parent),
        
        # 詳細な出力
        "-v",
        
        # 失敗時の詳細情報
        "--tb=long",
        
        # 並列実行を無効化（統合テストでは順次実行が推奨）
        "-x",
        
        # ログ出力を表示
        "--log-cli-level=INFO",
        
        # カバレッジレポート
        "--cov=src",
        "--cov-report=html:htmlcov/integration",
        "--cov-report=term-missing",
        
        # 警告を表示
        "-W", "ignore::DeprecationWarning",
        
        # マーカーでフィルタリング（必要に応じて）
        # "-m", "not performance",  # パフォーマンステストを除外する場合
    ]
    
    # 環境変数設定
    os.environ["TESTING"] = "1"
    os.environ["INTEGRATION_TEST"] = "1"
    
    # テスト実行
    exit_code = pytest.main(pytest_args)
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code) 