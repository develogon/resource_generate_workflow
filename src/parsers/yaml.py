"""YAMLパーサー."""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.validation import validate_file_path


class YAMLParser:
    """YAMLパーサー."""
    
    def __init__(self):
        """初期化."""
        self.loader = yaml.SafeLoader
    
    def parse_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """ファイルからYAMLをパース."""
        # ファイルパスのバリデーション
        validation_result = validate_file_path(
            file_path, 
            allowed_extensions=['.yml', '.yaml'],
            must_exist=True
        )
        
        if not validation_result["valid"]:
            raise ValueError(f"Invalid file path: {validation_result['errors']}")
        
        path = Path(file_path)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.parse(content)
            
        except Exception as e:
            raise ValueError(f"Failed to read file {path}: {str(e)}")
    
    def parse(self, content: str) -> Dict[str, Any]:
        """YAML文字列をパース."""
        if not content or not content.strip():
            return {}
        
        try:
            data = yaml.load(content, Loader=self.loader)
            
            # Noneの場合は空辞書を返す
            if data is None:
                return {}
            
            # 辞書でない場合はエラー
            if not isinstance(data, dict):
                raise ValueError(f"YAML content must be a dictionary, got {type(data)}")
            
            return data
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML content: {str(e)}")
    
    def parse_multiple(self, content: str) -> List[Dict[str, Any]]:
        """複数のYAMLドキュメントをパース."""
        if not content or not content.strip():
            return []
        
        try:
            documents = []
            for doc in yaml.load_all(content, Loader=self.loader):
                if doc is not None:
                    if isinstance(doc, dict):
                        documents.append(doc)
                    else:
                        raise ValueError(f"Each YAML document must be a dictionary, got {type(doc)}")
            
            return documents
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML content: {str(e)}")
    
    def validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """スキーマに基づくバリデーション."""
        errors = []
        warnings = []
        
        # 必須フィールドのチェック
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                errors.append(f"Required field missing: {field}")
            elif data[field] is None:
                errors.append(f"Required field is null: {field}")
        
        # フィールドタイプのチェック
        field_types = schema.get("properties", {})
        for field, type_spec in field_types.items():
            if field in data and data[field] is not None:
                expected_type = type_spec.get("type")
                value = data[field]
                
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Field '{field}' must be a string, got {type(value)}")
                elif expected_type == "integer" and not isinstance(value, int):
                    errors.append(f"Field '{field}' must be an integer, got {type(value)}")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field '{field}' must be a boolean, got {type(value)}")
                elif expected_type == "array" and not isinstance(value, list):
                    errors.append(f"Field '{field}' must be an array, got {type(value)}")
                elif expected_type == "object" and not isinstance(value, dict):
                    errors.append(f"Field '{field}' must be an object, got {type(value)}")
                
                # 値の範囲チェック
                if "minimum" in type_spec and isinstance(value, (int, float)):
                    if value < type_spec["minimum"]:
                        errors.append(f"Field '{field}' must be >= {type_spec['minimum']}, got {value}")
                
                if "maximum" in type_spec and isinstance(value, (int, float)):
                    if value > type_spec["maximum"]:
                        errors.append(f"Field '{field}' must be <= {type_spec['maximum']}, got {value}")
                
                # 文字列長チェック
                if "minLength" in type_spec and isinstance(value, str):
                    if len(value) < type_spec["minLength"]:
                        errors.append(f"Field '{field}' must be at least {type_spec['minLength']} characters, got {len(value)}")
                
                if "maxLength" in type_spec and isinstance(value, str):
                    if len(value) > type_spec["maxLength"]:
                        errors.append(f"Field '{field}' must be at most {type_spec['maxLength']} characters, got {len(value)}")
                
                # 列挙値チェック
                if "enum" in type_spec:
                    if value not in type_spec["enum"]:
                        errors.append(f"Field '{field}' must be one of {type_spec['enum']}, got '{value}'")
        
        # 追加フィールドのチェック
        if not schema.get("additionalProperties", True):
            allowed_fields = set(field_types.keys())
            for field in data.keys():
                if field not in allowed_fields:
                    warnings.append(f"Unknown field: {field}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


class ConfigParser(YAMLParser):
    """設定ファイル専用のYAMLパーサー."""
    
    def __init__(self):
        """初期化."""
        super().__init__()
        self.config_schema = {
            "type": "object",
            "required": ["lang", "title"],
            "properties": {
                "lang": {
                    "type": "string",
                    "enum": ["ja", "en", "zh", "ko"]
                },
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200
                },
                "description": {
                    "type": "string",
                    "maxLength": 1000
                },
                "max_concurrent_tasks": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100
                },
                "batch_size": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000
                },
                "timeout": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 3600
                },
                "output": {
                    "type": "object",
                    "properties": {
                        "formats": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["article", "script", "description", "tweet", "thumbnail"]
                            }
                        },
                        "directory": {
                            "type": "string",
                            "minLength": 1
                        }
                    }
                }
            },
            "additionalProperties": True
        }
    
    def parse_config(self, content: str) -> Dict[str, Any]:
        """設定ファイルをパースしてバリデーション."""
        data = self.parse(content)
        
        # スキーマバリデーション
        validation_result = self.validate_schema(data, self.config_schema)
        
        return {
            "config": data,
            "validation": validation_result
        }


class MetadataParser(YAMLParser):
    """メタデータ専用のYAMLパーサー."""
    
    def __init__(self):
        """初期化."""
        super().__init__()
        self.metadata_schema = {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "minLength": 1
                },
                "author": {
                    "type": "string"
                },
                "date": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "category": {
                    "type": "string"
                },
                "lang": {
                    "type": "string",
                    "enum": ["ja", "en", "zh", "ko"]
                },
                "draft": {
                    "type": "boolean"
                },
                "word_count": {
                    "type": "integer",
                    "minimum": 0
                },
                "reading_time": {
                    "type": "integer",
                    "minimum": 0
                }
            },
            "additionalProperties": True
        }
    
    def parse_metadata(self, content: str) -> Dict[str, Any]:
        """メタデータをパースしてバリデーション."""
        data = self.parse(content)
        
        # スキーマバリデーション
        validation_result = self.validate_schema(data, self.metadata_schema)
        
        # 日付フォーマットの検証
        if "date" in data and isinstance(data["date"], str):
            import re
            date_patterns = [
                r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO format
                r'^\d{4}/\d{2}/\d{2}$'   # YYYY/MM/DD
            ]
            
            if not any(re.match(pattern, data["date"]) for pattern in date_patterns):
                validation_result["warnings"] = validation_result.get("warnings", [])
                validation_result["warnings"].append("Date format should be YYYY-MM-DD, YYYY/MM/DD, or ISO format")
        
        return {
            "metadata": data,
            "validation": validation_result
        }
    
    def extract_from_frontmatter(self, content: str) -> Dict[str, Any]:
        """front matterからメタデータを抽出."""
        import frontmatter
        
        try:
            post = frontmatter.loads(content)
            metadata = post.metadata
            
            # バリデーション
            validation_result = self.validate_schema(metadata, self.metadata_schema)
            
            return {
                "metadata": metadata,
                "content": post.content,
                "validation": validation_result
            }
            
        except Exception as e:
            return {
                "metadata": {},
                "content": content,
                "validation": {
                    "valid": False,
                    "errors": [f"Failed to parse front matter: {str(e)}"],
                    "warnings": []
                }
            } 