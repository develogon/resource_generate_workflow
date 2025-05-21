"""
リソース生成ワークフローの設定パッケージ

このパッケージは、アプリケーションの設定を管理します。
settings.pyには一般設定、credentials.pyには認証情報が含まれています。
"""

import warnings
from .settings import *
from .credentials import CLAUDE_API_KEY, GITHUB_AUTH, AWS_AUTH, SLACK_AUTH, validate_credentials, mask_token

# 起動時に認証情報の検証を行う
credentials_status = validate_credentials()
if not credentials_status["is_valid"]:
    warnings.warn(
        f"以下の認証情報が設定されていません: {', '.join(credentials_status['missing'])}\n"
        "環境変数を設定するか、または.envファイルを使用してください。"
    ) 