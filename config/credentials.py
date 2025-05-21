"""
リソース生成ワークフローのAPI認証情報

このモジュールでは、外部サービスとの通信に必要なAPI認証情報を管理します。
本番環境では環境変数から読み込み、ローカル開発環境ではデフォルト値を使用します。

注意: .env ファイルや環境変数を使用してください。
"""

import os
from typing import Dict, Any

# Claude API認証情報
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")

# GitHub認証情報
GITHUB_AUTH = {
    "token": os.environ.get("GITHUB_TOKEN", ""),
    "username": os.environ.get("GITHUB_USERNAME", "develogon"),
    "repository": os.environ.get("GITHUB_REPOSITORY", "til"),
}

# AWS認証情報 (S3ストレージ用)
AWS_AUTH = {
    "access_key_id": os.environ.get("AWS_ACCESS_KEY_ID", ""),
    "secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
}

# Slack認証情報
SLACK_AUTH = {
    "token": os.environ.get("SLACK_API_TOKEN", ""),
    "webhook_url": os.environ.get("SLACK_WEBHOOK_URL", ""),
}

def validate_credentials() -> Dict[str, Any]:
    """
    必須の認証情報が設定されているか検証します。
    
    戻り値:
        Dict[str, Any]: 検証結果と欠落している認証情報のリスト
    """
    missing_credentials = []
    
    # Claude API認証情報の検証
    if not CLAUDE_API_KEY:
        missing_credentials.append("CLAUDE_API_KEY")
    
    # GitHub認証情報の検証
    if not GITHUB_AUTH["token"]:
        missing_credentials.append("GITHUB_TOKEN")
    if not GITHUB_AUTH["repository"]:
        missing_credentials.append("GITHUB_REPOSITORY")
    
    # AWS認証情報の検証
    if not AWS_AUTH["access_key_id"]:
        missing_credentials.append("AWS_ACCESS_KEY_ID")
    if not AWS_AUTH["secret_access_key"]:
        missing_credentials.append("AWS_SECRET_ACCESS_KEY")
    
    # Slack認証情報の検証 (Webhookまたはトークンが必要)
    if not (SLACK_AUTH["token"] or SLACK_AUTH["webhook_url"]):
        missing_credentials.append("SLACK_API_TOKEN or SLACK_WEBHOOK_URL")
    
    return {
        "is_valid": len(missing_credentials) == 0,
        "missing": missing_credentials
    }

# 認証情報のトークン化 (ログ出力時などにマスクするため)
def mask_token(token: str, visible_chars: int = 4) -> str:
    """
    トークンの一部をマスクします。
    
    引数:
        token (str): マスクするトークン
        visible_chars (int): 表示する文字数
        
    戻り値:
        str: マスクされたトークン
    """
    if not token or len(token) <= visible_chars:
        return token
    
    return token[:visible_chars] + "*" * (len(token) - visible_chars) 