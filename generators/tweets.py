"""
ツイート生成を担当するモジュール。
Claude APIを使用して記事内容からツイートのセットを生成する。
"""
import re
import csv
from io import StringIO
from typing import Dict, Any, List, Optional, Set


from core.content_generator import ContentGenerator


class TweetsGenerator(ContentGenerator):
    """
    ツイート生成を担当するクラス。
    ContentGeneratorを継承し、ツイート生成特有の処理を実装する。
    """
    
    def __init__(self, claude_service: Any, file_manager: Any, template_dir: str = "templates", max_length: int = 280):
        """
        TweetsGeneratorを初期化する。
        
        Args:
            claude_service (Any): Claude APIサービス
            file_manager (Any): ファイル管理サービス
            template_dir (str, optional): テンプレートディレクトリのパス
            max_length (int, optional): ツイートの最大文字数
        """
        super().__init__(claude_service, file_manager, template_dir)
        self.max_length = max_length
        self.required_fields = ["tweet_text", "hashtags", "topic", "character_count"]
    
    def generate(self, input_data: Dict[str, Any]) -> str:
        """
        ツイートを生成する。
        
        Args:
            input_data (dict): 生成に必要な入力データ
                - ARTICLE_CONTENT: 元の記事コンテンツ
                - template_path: テンプレートファイルのパス
                - max_tweets (optional): 生成するツイートの最大数
                - hashtags (optional): 追加するハッシュタグのリスト
        
        Returns:
            str: 生成されたツイートCSV
        """
        return super().generate(input_data)
    
    def format_output(self, raw_content: str) -> str:
        """
        生成されたツイートコンテンツをCSV形式に整形する。
        
        Args:
            raw_content (str): 生成された生のツイートコンテンツ
        
        Returns:
            str: 整形されたCSV形式のツイート
        """
        if not raw_content or not raw_content.strip():
            # 空の場合はヘッダーのみのCSVを返す
            return ",".join(self.required_fields)
        
        # CSVフォーマットを検出し整形
        try:
            # CSVリーダーでパース
            reader = csv.reader(StringIO(raw_content))
            rows = list(reader)
            
            # ヘッダー行の検出と確認
            has_required_headers = False
            if rows and len(rows) > 0:
                headers = rows[0]
                # ヘッダーが既に存在するか確認
                if all(field in headers for field in self.required_fields):
                    has_required_headers = True
            
            # ヘッダーがない場合は追加
            if not has_required_headers:
                new_rows = [self.required_fields]
                
                # 既存データの処理
                for row in rows:
                    if not row:  # 空行をスキップ
                        continue
                    
                    # データ行の処理
                    if len(row) == 1:  # テキストのみの場合
                        tweet_text = row[0]
                        # 引用符や余分な文字を削除
                        tweet_text = re.sub(r'^["\']+|["\']+$', '', tweet_text)
                        
                        # 文字数を確認して調整
                        if not self.check_tweet_length(tweet_text):
                            tweet_text = tweet_text[:self.max_length]
                        
                        # データ行を新しいフォーマットに変換
                        new_row = [
                            tweet_text,
                            "",  # hashtags
                            "",  # topic
                            str(len(tweet_text))  # character_count
                        ]
                        new_rows.append(new_row)
                    elif len(row) >= 2:  # 複数カラムがある場合
                        # 既存データをできるだけ維持しつつ新フォーマットに変換
                        tweet_text = row[0]
                        
                        # 既存のハッシュタグがあれば使用
                        hashtags = row[1] if len(row) > 1 else ""
                        
                        # トピックがあれば使用
                        topic = row[2] if len(row) > 2 else ""
                        
                        # 文字数をカウント
                        character_count = str(len(tweet_text))
                        
                        new_row = [tweet_text, hashtags, topic, character_count]
                        new_rows.append(new_row)
                
                # 新しい形式に変換されたCSVを生成
                output = StringIO()
                writer = csv.writer(output)
                writer.writerows(new_rows)
                return output.getvalue()
            
            # 既にヘッダーがある場合はそのまま返す
            return raw_content
            
        except Exception as e:
            # CSVパースに失敗した場合、単純なテキストとして処理
            lines = raw_content.strip().split('\n')
            output = StringIO()
            writer = csv.writer(output)
            
            # ヘッダー行を追加
            writer.writerow(self.required_fields)
            
            # 各行をツイートとして処理
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 引用符や余分な文字を削除
                tweet_text = re.sub(r'^["\']+|["\']+$', '', line)
                
                # 文字数を確認して調整
                if not self.check_tweet_length(tweet_text):
                    tweet_text = tweet_text[:self.max_length]
                
                # 新しい行を追加
                writer.writerow([
                    tweet_text,
                    "",  # hashtags
                    "",  # topic
                    str(len(tweet_text))  # character_count
                ])
            
            return output.getvalue()
    
    def validate_content(self, content: str) -> bool:
        """
        生成されたツイートコンテンツを検証する。
        
        Args:
            content (str): 検証するツイートコンテンツ
        
        Returns:
            bool: コンテンツが有効な場合はTrue、そうでない場合はFalse
        """
        if not content or not content.strip():
            return False
        
        try:
            # CSVとして解析
            reader = csv.reader(StringIO(content))
            rows = list(reader)
            
            # 最低限ヘッダー行と1行のデータがあるべき
            if len(rows) < 2:
                return False
            
            # ヘッダー行の検証
            headers = rows[0]
            if not all(field in headers for field in ["tweet_text"]):
                return False
            
            # データ行を検証
            for row in rows[1:]:
                if not row or len(row) < 1 or not row[0].strip():
                    continue  # 空行はスキップ
                
                tweet_text = row[0]
                # 文字数チェック
                if not self.check_tweet_length(tweet_text):
                    return False
            
            # 少なくとも1つの有効なツイートがあるか確認
            valid_tweets = [row for row in rows[1:] if row and len(row) > 0 and row[0].strip()]
            return len(valid_tweets) > 0
            
        except Exception:
            return False
    
    def check_tweet_length(self, tweet_text: str) -> bool:
        """
        ツイートの長さが制限内かチェックする。
        
        Args:
            tweet_text (str): チェックするツイートのテキスト
        
        Returns:
            bool: 長さが制限内の場合はTrue、そうでない場合はFalse
        """
        return len(tweet_text) <= self.max_length 