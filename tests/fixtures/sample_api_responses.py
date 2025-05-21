"""
APIサービスのテスト用サンプルレスポンスデータ
"""

# サンプルAPIレスポンス (一般)
SAMPLE_API_RESPONSE = {
    "status": "success",
    "data": {
        "id": "response_123",
        "timestamp": "2023-05-01T12:00:00Z"
    }
}

# サンプルAPIエラーレスポンス
SAMPLE_API_ERROR_RESPONSE = {
    "status": "error",
    "error": {
        "code": "rate_limit_exceeded",
        "message": "API rate limit exceeded, please retry after 60 seconds"
    }
}

# サンプルClaudeAPIレスポンス
SAMPLE_CLAUDE_RESPONSE = {
    "id": "msg_01234abcdef",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": "# サンプルレスポンス\n\nこれはClaudeからのサンプルレスポンスです。\n\n```yaml\ntitle: サンプルYAML\nkey: value\n```\n\nMarkdown形式のテキストが含まれています。"
        }
    ],
    "model": "claude-3-7-sonnet-20250219",
    "stop_reason": "end_turn",
    "stop_sequence": null,
    "usage": {
        "input_tokens": 150,
        "output_tokens": 89
    }
}

# サンプルGitHubAPIレスポンス (コンテンツ取得)
SAMPLE_GITHUB_CONTENT_RESPONSE = {
    "name": "example.md",
    "path": "docs/example.md",
    "sha": "abcdef1234567890",
    "size": 1024,
    "url": "https://api.github.com/repos/owner/repo/contents/docs/example.md",
    "html_url": "https://github.com/owner/repo/blob/main/docs/example.md",
    "git_url": "https://api.github.com/repos/owner/repo/git/blobs/abcdef1234567890",
    "download_url": "https://raw.githubusercontent.com/owner/repo/main/docs/example.md",
    "type": "file",
    "content": "IyBFeGFtcGxlIE1hcmtkb3duCgpUaGlzIGlzIGEgc2FtcGxlIE1hcmtkb3duIGZpbGUu",
    "encoding": "base64",
    "_links": {
        "self": "https://api.github.com/repos/owner/repo/contents/docs/example.md",
        "git": "https://api.github.com/repos/owner/repo/git/blobs/abcdef1234567890",
        "html": "https://github.com/owner/repo/blob/main/docs/example.md"
    }
}

# サンプルS3アップロードレスポンス
SAMPLE_S3_UPLOAD_RESPONSE = {
    "ETag": "\"abcdef1234567890\"",
    "Location": "https://bucket-name.s3.region.amazonaws.com/path/to/image.png",
    "key": "path/to/image.png",
    "Bucket": "bucket-name"
}

# サンプルSlack通知レスポンス
SAMPLE_SLACK_RESPONSE = {
    "ok": True,
    "channel": "C1234567890",
    "ts": "1234567890.123456",
    "message": {
        "text": "テスト通知",
        "username": "bot",
        "bot_id": "B12345678",
        "type": "message",
        "subtype": "bot_message",
        "ts": "1234567890.123456"
    }
} 