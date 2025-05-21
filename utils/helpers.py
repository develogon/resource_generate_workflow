import os
import re


def sanitize_filename(filename):
    """
    ファイル名に使用できない文字を置換して安全なファイル名に変換します。
    
    Parameters
    ----------
    filename : str
        変換するファイル名
        
    Returns
    -------
    str
        安全に変換されたファイル名
    """
    # ファイルシステムで使用できない文字を置換
    # Windows, macOS, Linuxの主な制限文字に対応
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # スペースをアンダースコアに置換
    sanitized = sanitized.replace(' ', '_')
    
    return sanitized


def ensure_directory_exists(directory_path):
    """
    指定されたディレクトリが存在しない場合は作成します。
    
    Parameters
    ----------
    directory_path : str
        確認または作成するディレクトリのパス
        
    Returns
    -------
    bool
        ディレクトリが存在する（または作成された）場合はTrue
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        return True
    
    return os.path.isdir(directory_path)


def extract_title(markdown_content):
    """
    Markdownコンテンツから最初の見出し（# で始まる行）を抽出してタイトルとして返します。
    
    Parameters
    ----------
    markdown_content : str
        Markdownフォーマットのコンテンツ
        
    Returns
    -------
    str or None
        抽出されたタイトル、見つからない場合はNone
    """
    # 先頭の#で始まる行を検索
    match = re.search(r'^# (.+)$', markdown_content, re.MULTILINE)
    
    if match:
        return match.group(1).strip()
    
    return None 