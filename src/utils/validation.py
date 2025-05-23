"""バリデーションユーティリティ."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..config.constants import CODE_EXTENSIONS, IMAGE_EXTENSIONS, MARKDOWN_EXTENSIONS


def validate_markdown_content(content: str) -> Dict[str, Any]:
    """Markdownコンテンツのバリデーション."""
    errors = []
    warnings = []
    stats = {
        "total_lines": 0,
        "heading_count": 0,
        "code_block_count": 0,
        "link_count": 0,
        "image_count": 0,
        "character_count": len(content),
        "word_count": 0
    }
    
    if not content or not content.strip():
        errors.append("Content is empty or contains only whitespace")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "stats": stats
        }
    
    lines = content.split('\n')
    stats["total_lines"] = len(lines)
    
    # 基本的な統計を収集
    word_count = 0
    in_code_block = False
    code_block_lang = None
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # 単語数カウント（コードブロック内は除外）
        if not in_code_block and line_stripped:
            # Markdownの構文を除外した単語数
            clean_line = re.sub(r'[#*`\[\]()_-]', ' ', line_stripped)
            words = clean_line.split()
            word_count += len([w for w in words if w.strip()])
        
        # 見出しのチェック
        if line_stripped.startswith('#'):
            stats["heading_count"] += 1
            
            # 見出しレベルのチェック
            heading_level = len(line_stripped) - len(line_stripped.lstrip('#'))
            if heading_level > 6:
                warnings.append(f"Line {i+1}: Heading level {heading_level} exceeds maximum (6)")
            
            # 見出しテキストのチェック
            heading_text = line_stripped.lstrip('#').strip()
            if not heading_text:
                errors.append(f"Line {i+1}: Empty heading")
        
        # コードブロックのチェック
        if line_stripped.startswith('```'):
            if not in_code_block:
                in_code_block = True
                stats["code_block_count"] += 1
                code_block_lang = line_stripped[3:].strip()
            else:
                in_code_block = False
                code_block_lang = None
        
        # リンクのチェック
        link_pattern = r'\[([^\]]*)\]\(([^)]*)\)'
        links = re.findall(link_pattern, line)
        stats["link_count"] += len(links)
        
        for link_text, link_url in links:
            if not link_text.strip():
                warnings.append(f"Line {i+1}: Empty link text")
            if not link_url.strip():
                errors.append(f"Line {i+1}: Empty link URL")
        
        # 画像のチェック
        image_pattern = r'!\[([^\]]*)\]\(([^)]*)\)'
        images = re.findall(image_pattern, line)
        stats["image_count"] += len(images)
        
        for alt_text, image_url in images:
            if not alt_text.strip():
                warnings.append(f"Line {i+1}: Missing alt text for image")
            if not image_url.strip():
                errors.append(f"Line {i+1}: Empty image URL")
    
    stats["word_count"] = word_count
    
    # 最終的なコードブロックのチェック
    if in_code_block:
        errors.append("Unclosed code block detected")
    
    # 構造的な問題のチェック
    if stats["heading_count"] == 0:
        warnings.append("No headings found - consider adding structure")
    
    if stats["character_count"] < 100:
        warnings.append("Content is very short (less than 100 characters)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": stats
    }


def validate_file_path(
    file_path: Union[str, Path],
    allowed_extensions: Optional[List[str]] = None,
    must_exist: bool = True,
    max_size_mb: Optional[float] = None
) -> Dict[str, Any]:
    """ファイルパスのバリデーション."""
    errors = []
    warnings = []
    
    # Pathオブジェクトに変換
    if isinstance(file_path, str):
        if not file_path.strip():  # 空文字列のチェックを先に行う
            errors.append("File path is empty")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "path": Path(""),
                "exists": False
            }
        path = Path(file_path)
    else:
        path = file_path
    
    # 基本的なパスチェック（空のPathオブジェクトのチェック）
    if not str(path) or str(path) == '.':
        errors.append("File path is empty")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "path": path,
            "exists": False
        }
    
    # 存在チェック
    exists = path.exists()
    if must_exist and not exists:
        errors.append(f"File does not exist: {path}")
    
    if exists:
        # ファイルかディレクトリかのチェック
        if path.is_dir():
            warnings.append("Path points to a directory, not a file")
        
        # ファイルサイズチェック
        if path.is_file() and max_size_mb:
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > max_size_mb:
                errors.append(f"File size ({file_size_mb:.2f}MB) exceeds limit ({max_size_mb}MB)")
        
        # 読み取り権限チェック
        try:
            with open(path, 'r', encoding='utf-8') as f:
                f.read(1)  # 1文字だけ読んで権限確認
        except PermissionError:
            errors.append("Permission denied: Cannot read file")
        except UnicodeDecodeError:
            warnings.append("File may not be UTF-8 encoded")
        except Exception as e:
            warnings.append(f"Could not read file: {str(e)}")
    
    # 拡張子チェック
    if allowed_extensions:
        file_extension = path.suffix.lower()
        if file_extension not in [ext.lower() for ext in allowed_extensions]:
            errors.append(f"Invalid file extension: {file_extension}. Allowed: {allowed_extensions}")
    
    # パスセキュリティチェック
    try:
        resolved_path = path.resolve()
        if '../' in str(path) or '..' in path.parts:
            warnings.append("Path contains parent directory references")
    except Exception:
        warnings.append("Could not resolve absolute path")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "path": path,
        "exists": exists,
        "extension": path.suffix.lower() if path.suffix else None
    }


def validate_content_structure(content: Dict[str, Any]) -> Dict[str, Any]:
    """コンテンツ構造のバリデーション."""
    errors = []
    warnings = []
    
    required_fields = ["id", "title", "content"]
    
    # 必須フィールドのチェック
    for field in required_fields:
        if field not in content:
            errors.append(f"Required field missing: {field}")
        elif not content[field] or (isinstance(content[field], str) and not content[field].strip()):
            errors.append(f"Required field is empty: {field}")
    
    # IDの形式チェック
    if "id" in content and content["id"]:
        id_value = content["id"]
        if not isinstance(id_value, str):
            errors.append("ID must be a string")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', id_value):
            warnings.append("ID contains special characters that may cause issues")
    
    # タイトルの長さチェック
    if "title" in content and content["title"]:
        title = content["title"]
        if isinstance(title, str):
            if len(title) > 200:
                warnings.append("Title is very long (over 200 characters)")
            elif len(title) < 5:
                warnings.append("Title is very short (less than 5 characters)")
    
    # コンテンツの長さチェック
    if "content" in content and content["content"]:
        content_text = content["content"]
        if isinstance(content_text, str):
            if len(content_text) > 100000:
                warnings.append("Content is very long (over 100,000 characters)")
            elif len(content_text) < 50:
                warnings.append("Content is very short (less than 50 characters)")
    
    # メタデータの型チェック
    if "metadata" in content:
        metadata = content["metadata"]
        if not isinstance(metadata, dict):
            errors.append("Metadata must be a dictionary")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_workflow_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """ワークフロー設定のバリデーション."""
    errors = []
    warnings = []
    
    # 基本フィールドのチェック
    required_fields = ["lang", "title"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Required field missing: {field}")
        elif not config[field] or not str(config[field]).strip():
            errors.append(f"Required field is empty: {field}")
    
    # 言語設定のチェック
    if "lang" in config:
        lang = config["lang"]
        supported_languages = ["ja", "en", "zh", "ko"]
        if lang not in supported_languages:
            warnings.append(f"Language '{lang}' may not be fully supported. Supported: {supported_languages}")
    
    # 並行実行数のチェック
    if "max_concurrent_tasks" in config:
        max_concurrent = config["max_concurrent_tasks"]
        if not isinstance(max_concurrent, int) or max_concurrent <= 0:
            errors.append("max_concurrent_tasks must be a positive integer")
        elif max_concurrent > 50:
            warnings.append("max_concurrent_tasks is very high, may cause resource issues")
    
    # バッチサイズのチェック
    if "batch_size" in config:
        batch_size = config["batch_size"]
        if not isinstance(batch_size, int) or batch_size <= 0:
            errors.append("batch_size must be a positive integer")
        elif batch_size > 100:
            warnings.append("batch_size is very high, may cause memory issues")
    
    # タイムアウトのチェック
    if "timeout" in config:
        timeout = config["timeout"]
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            errors.append("timeout must be a positive number")
        elif timeout > 3600:
            warnings.append("timeout is very high (over 1 hour)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_api_response(response: Dict[str, Any], expected_fields: List[str]) -> Dict[str, Any]:
    """API レスポンスのバリデーション."""
    errors = []
    warnings = []
    
    if not isinstance(response, dict):
        errors.append("Response must be a dictionary")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings
        }
    
    # 必須フィールドのチェック
    for field in expected_fields:
        if field not in response:
            errors.append(f"Required field missing: {field}")
    
    # 一般的なエラーフィールドのチェック
    if "error" in response and response["error"]:
        errors.append(f"API returned error: {response['error']}")
    
    # データの型チェック
    if "data" in response:
        data = response["data"]
        if data is None:
            warnings.append("Response data is null")
        elif isinstance(data, str) and not data.strip():
            warnings.append("Response data is empty string")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    } 