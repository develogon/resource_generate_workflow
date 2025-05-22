#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""設定管理モジュール

このモジュールは、システムの設定を管理します。
環境変数や設定ファイルから設定を読み込み、デフォルト値との統合や検証を行います。
"""

import os
import sys
import json
import yaml
import logging
from typing import Dict, Any, Optional

# ロガーの設定
logger = logging.getLogger(__name__)

# デフォルト設定ファイルのパス
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.default.yaml")


def load_default_config() -> Dict[str, Any]:
    """
    デフォルト設定ファイルから設定を読み込む

    Returns:
        Dict[str, Any]: デフォルト設定
    """
    try:
        if os.path.exists(DEFAULT_CONFIG_PATH):
            logger.debug(f"デフォルト設定ファイルを読み込みます: {DEFAULT_CONFIG_PATH}")
            with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"デフォルト設定ファイルが見つかりません: {DEFAULT_CONFIG_PATH}")
            return {}
    except Exception as e:
        logger.error(f"デフォルト設定ファイルの読み込み中にエラーが発生しました: {str(e)}")
        return {}


def load_env_vars() -> Dict[str, Any]:
    """
    環境変数から設定を読み込む

    Returns:
        Dict[str, Any]: 環境変数から読み込んだ設定
    """
    config = {}
    
    # APIキー
    if os.environ.get("CLAUDE_API_KEY"):
        if "api" not in config:
            config["api"] = {}
        if "claude" not in config["api"]:
            config["api"]["claude"] = {}
        config["api"]["claude"]["api_key"] = os.environ.get("CLAUDE_API_KEY")
    
    if os.environ.get("OPENAI_API_KEY"):
        if "api" not in config:
            config["api"] = {}
        if "openai" not in config["api"]:
            config["api"]["openai"] = {}
        config["api"]["openai"]["api_key"] = os.environ.get("OPENAI_API_KEY")
    
    # GitHub設定
    if os.environ.get("GITHUB_TOKEN"):
        if "github" not in config:
            config["github"] = {}
        config["github"]["token"] = os.environ.get("GITHUB_TOKEN")
    
    if os.environ.get("GITHUB_OWNER"):
        if "github" not in config:
            config["github"] = {}
        config["github"]["owner"] = os.environ.get("GITHUB_OWNER")
    
    if os.environ.get("GITHUB_REPO"):
        if "github" not in config:
            config["github"] = {}
        config["github"]["repo"] = os.environ.get("GITHUB_REPO")
    
    # AWS設定
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        if "aws" not in config:
            config["aws"] = {}
        config["aws"]["access_key_id"] = os.environ.get("AWS_ACCESS_KEY_ID")
        config["aws"]["secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY")
    
    if os.environ.get("S3_BUCKET"):
        if "s3" not in config:
            config["s3"] = {}
        config["s3"]["bucket"] = os.environ.get("S3_BUCKET")
    
    # Slack設定
    if os.environ.get("SLACK_WEBHOOK_URL"):
        if "slack" not in config:
            config["slack"] = {}
        config["slack"]["webhook_url"] = os.environ.get("SLACK_WEBHOOK_URL")
    
    return config


def load_config_file(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    設定ファイルから設定を読み込む

    Args:
        config_path: 設定ファイルのパス。指定がない場合はデフォルトのパスを使用。

    Returns:
        Dict[str, Any]: 設定ファイルから読み込んだ設定
    """
    if not config_path:
        # デフォルトのパス候補
        config_paths = [
            "config.yaml",
            "config.yml",
            "config.json",
            os.path.expanduser("~/.resource-workflow/config.yaml"),
            os.path.expanduser("~/.resource-workflow/config.json")
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                config_path = path
                break
    
    if not config_path or not os.path.exists(config_path):
        logger.debug("設定ファイルが見つかりませんでした。デフォルト設定を使用します。")
        return {}
    
    logger.info(f"設定ファイルを読み込みます: {config_path}")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.endswith(".json"):
                return json.load(f)
            else:  # .yaml または .yml
                return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"設定ファイルの読み込み中にエラーが発生しました: {str(e)}")
        return {}


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    設定を再帰的にマージする

    Args:
        base: ベースとなる設定
        override: 上書きする設定

    Returns:
        Dict[str, Any]: マージされた設定
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    設定を検証し、必要に応じて値を調整する

    Args:
        config: 検証する設定

    Returns:
        Dict[str, Any]: 検証済みの設定
    """
    # APIキーのチェック
    if "api" in config:
        if "claude" in config["api"] and not config["api"]["claude"].get("api_key"):
            logger.warning("Claude APIキーが設定されていません。Claude関連の機能は使用できません。")
        
        if "openai" in config["api"] and not config["api"]["openai"].get("api_key"):
            logger.warning("OpenAI APIキーが設定されていません。OpenAI関連の機能は使用できません。")
    
    # GitHub設定のチェック
    if "github" in config:
        if not config["github"].get("token"):
            logger.warning("GitHub APIトークンが設定されていません。GitHub関連の機能は使用できません。")
        
        if not config["github"].get("owner") or not config["github"].get("repo"):
            logger.warning("GitHubのオーナーまたはリポジトリが設定されていません。GitHub関連の機能は使用できません。")
    
    # S3設定のチェック
    if "s3" in config:
        if not config["s3"].get("bucket"):
            logger.warning("S3バケットが設定されていません。S3関連の機能は使用できません。")
    
    # ディレクトリパスの絶対パス化
    for dir_key in ["workspace_dir", "checkpoint_dir", "output_dir", "temp_dir"]:
        if dir_key in config and not os.path.isabs(config[dir_key]):
            config[dir_key] = os.path.abspath(config[dir_key])
    
    # ディレクトリの存在確認と作成
    for dir_key in ["checkpoint_dir", "output_dir", "temp_dir"]:
        if dir_key in config:
            os.makedirs(config[dir_key], exist_ok=True)
    
    return config


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    設定を読み込む

    Args:
        config_path: 設定ファイルのパス

    Returns:
        Dict[str, Any]: 読み込まれた設定
    """
    # デフォルト設定をベースにする
    config = load_default_config()
    
    # 設定ファイルから読み込む
    file_config = load_config_file(config_path)
    if file_config:
        config = merge_configs(config, file_config)
    
    # 環境変数から読み込む（最優先）
    env_config = load_env_vars()
    if env_config:
        config = merge_configs(config, env_config)
    
    # 設定の検証と調整
    config = validate_config(config)
    
    return config


def get_config() -> Dict[str, Any]:
    """
    現在の設定を取得する（シングルトンパターン）

    Returns:
        Dict[str, Any]: 現在の設定
    """
    if not hasattr(get_config, "_config"):
        get_config._config = load_config()
    
    return get_config._config 