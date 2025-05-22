"""ワークフローエンジン

このモジュールは、システム全体を制御し、実行フローを管理します。
コンテンツプロセッサ、ジェネレータシステム、タスク管理システム、チェックポイント管理を連携させます。
"""

import os
import logging
from typing import Dict, Any, Optional, List

from app.workflow.task_manager import TaskManager, TaskType
from app.workflow.checkpoint import CheckpointManager

# ロガーの設定
logger = logging.getLogger(__name__)


class WorkflowEngine:
    """ワークフローエンジン"""
    
    def __init__(self, config: Dict = None):
        """
        初期化

        Args:
            config: 設定情報
        """
        self.config = config or {}
        self.task_manager = TaskManager()
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir=self.config.get("checkpoint_dir", "checkpoints")
        )
    
    def start(self, input_path: str) -> bool:
        """
        ワークフローを開始する

        Args:
            input_path: 入力ファイルパス

        Returns:
            bool: 開始が成功した場合はTrue、それ以外はFalse
        """
        try:
            logger.info(f"ワークフローを開始します: {input_path}")
            
            # 入力ファイルの存在確認
            if not os.path.exists(input_path):
                logger.error(f"入力ファイルが見つかりません: {input_path}")
                return False
            
            # 初期タスクの登録
            self._register_initial_tasks(input_path)
            
            # 初期チェックポイントの保存
            initial_state = {
                "input_path": input_path,
                "stage": "INITIALIZED"
            }
            self.checkpoint_manager.save_checkpoint("INITIAL", initial_state)
            
            # タスク実行ループを開始
            return self.execute_task_loop()
            
        except Exception as e:
            logger.exception(f"ワークフロー開始中にエラーが発生しました: {str(e)}")
            self.handle_error(e, {"input_path": input_path})
            return False
    
    def resume(self, checkpoint_id: str = None) -> bool:
        """
        チェックポイントからワークフローを再開する

        Args:
            checkpoint_id: 再開するチェックポイントID（指定がない場合は最新のチェックポイント）

        Returns:
            bool: 再開が成功した場合はTrue、それ以外はFalse
        """
        try:
            # チェックポイントの読み込み
            if checkpoint_id:
                logger.info(f"チェックポイントからワークフローを再開します: {checkpoint_id}")
                checkpoint_data = self.checkpoint_manager.load_checkpoint(checkpoint_id)
            else:
                logger.info("最新のチェックポイントからワークフローを再開します")
                checkpoint_data = self.checkpoint_manager.load_latest_checkpoint()
            
            if not checkpoint_data:
                logger.error("再開可能なチェックポイントが見つかりません")
                return False
            
            # チェックポイントからの復元
            result = self.checkpoint_manager.restore_from_checkpoint(checkpoint_data["id"])
            if not result:
                logger.error("チェックポイントからの復元に失敗しました")
                return False
            
            # タスク実行ループを再開
            return self.execute_task_loop()
            
        except Exception as e:
            logger.exception(f"ワークフロー再開中にエラーが発生しました: {str(e)}")
            self.handle_error(e, {"checkpoint_id": checkpoint_id})
            return False
    
    def execute_task_loop(self) -> bool:
        """
        タスク実行ループ

        Returns:
            bool: すべてのタスクが正常に実行された場合はTrue、それ以外はFalse
        """
        try:
            while True:
                # 次の実行可能タスクを取得
                task = self.task_manager.get_next_executable_task()
                if not task:
                    logger.info("実行可能なタスクがありません。ワークフローを終了します。")
                    break
                
                # タスクを実行
                logger.info(f"タスク実行: {task['id']} ({task['type']})")
                try:
                    # タスクタイプに応じた処理を実行
                    result = self._execute_task(task)
                    
                    # タスクを完了としてマーク
                    self.task_manager.mark_as_completed(task["id"], result)
                    
                    # タスク実行結果に基づいて次のタスクを登録
                    self._register_next_tasks(result)
                    
                    # チェックポイントを保存
                    state = {
                        "last_completed_task": task["id"],
                        "task_type": task["type"]
                    }
                    self.checkpoint_manager.save_checkpoint("TASK", state)
                    
                except Exception as e:
                    logger.exception(f"タスク実行中にエラーが発生しました: {str(e)}")
                    self.task_manager.mark_as_failed(task["id"], e)
                    
                    # 再試行可能な場合は再試行
                    if self.task_manager.retry_task(task["id"]):
                        logger.info(f"タスクを再試行します: {task['id']}")
                    else:
                        # エラー処理
                        logger.error(f"タスクの再試行回数が上限に達しました: {task['id']}")
                        self.handle_error(e, {"task_id": task["id"]})
                        return False
            
            logger.info("ワークフローが正常に完了しました")
            return True
            
        except Exception as e:
            logger.exception(f"タスク実行ループ中にエラーが発生しました: {str(e)}")
            self.handle_error(e, {})
            return False
    
    def handle_error(self, error: Exception, context: Dict) -> bool:
        """
        エラー処理

        Args:
            error: 発生したエラー
            context: エラーコンテキスト情報

        Returns:
            bool: エラー処理が成功した場合はTrue、それ以外はFalse
        """
        try:
            logger.error(f"エラーハンドリング: {str(error)}")
            
            # エラーチェックポイントの保存
            error_state = {
                "error": str(error),
                "context": context
            }
            self.checkpoint_manager.save_checkpoint("ERROR", error_state)
            
            # エラー通知の送信
            # 実際の実装では、Slack通知などを行う
            
            return False
            
        except Exception as e:
            logger.exception(f"エラー処理中に例外が発生しました: {str(e)}")
            return False
    
    def _register_initial_tasks(self, input_path: str) -> None:
        """
        初期タスクを登録する

        Args:
            input_path: 入力ファイルパス
        """
        # チャプター分割タスク
        self.task_manager.register_task({
            "type": TaskType.FILE_OPERATION,
            "params": {
                "operation": "SPLIT_CHAPTERS",
                "input_path": input_path
            }
        })
        
        logger.info(f"初期タスクを登録しました: {input_path} のチャプター分割")

    def _register_next_tasks(self, task_result: Dict) -> None:
        """
        タスク実行結果に基づいて次のタスクを登録する

        Args:
            task_result: タスク実行結果
        """
        if not task_result.get("success", False):
            logger.warning("タスクが失敗したため、次のタスクを登録しません")
            return
        
        # チャプター分割結果からセクション分割タスクを登録
        if "chapters" in task_result:
            chapters = task_result.get("chapters", [])
            input_path = task_result.get("input_path", "")
            
            logger.info(f"{len(chapters)}個のチャプターに対するタスクを登録します")
            
            for idx, chapter in enumerate(chapters, 1):
                # チャプターごとのセクション分割タスクを登録
                task_id = self.task_manager.register_task({
                    "type": TaskType.FILE_OPERATION,
                    "params": {
                        "operation": "SPLIT_SECTIONS",
                        "chapter_content": chapter["content"],
                        "chapter_title": chapter["title"],
                        "chapter_index": idx,
                        "input_path": input_path
                    }
                })
                
                logger.info(f"チャプター分割タスクを登録しました: {task_id} - {chapter['title']}")
        
        # セクション分割結果からセクション構造解析タスクを登録
        elif "sections" in task_result:
            sections = task_result.get("sections", [])
            
            logger.info(f"{len(sections)}個のセクションに対するタスクを登録します")
            
            for idx, section in enumerate(sections, 1):
                # セクションごとの構造解析タスクを登録
                task_id = self.task_manager.register_task({
                    "type": TaskType.API_CALL,
                    "params": {
                        "api": "CLAUDE",
                        "operation": "ANALYZE_STRUCTURE",
                        "section_content": section["content"],
                        "section_title": section["title"],
                        "section_index": idx
                    }
                })
                
                logger.info(f"セクション構造解析タスクを登録しました: {task_id} - {section['title']}")
        
        # セクション構造解析結果から記事生成タスクを登録
        elif "operation" in task_result and task_result["operation"] == "ANALYZE_STRUCTURE":
            section_title = task_result.get("section_title", "")
            section_index = task_result.get("section_index", 0)
            analysis = task_result.get("analysis", "")
            
            # 記事生成タスクを登録
            task_id = self.task_manager.register_task({
                "type": TaskType.API_CALL,
                "params": {
                    "api": "CLAUDE",
                    "operation": "GENERATE_ARTICLE",
                    "section_title": section_title,
                    "section_index": section_index,
                    "analysis": analysis
                }
            })
            
            logger.info(f"記事生成タスクを登録しました: {task_id} - {section_title}")
            
            # GitHub操作タスクを登録
            task_id = self.task_manager.register_task({
                "type": TaskType.GITHUB_OPERATION,
                "params": {
                    "operation": "PUSH_STRUCTURE",
                    "section_title": section_title,
                    "section_index": section_index,
                    "analysis": analysis
                }
            })
            
            logger.info(f"GitHub操作タスクを登録しました: {task_id} - {section_title}")
                
        # 記事生成結果からスクリプト生成タスクとツイート生成タスクを登録
        elif "operation" in task_result and task_result["operation"] == "GENERATE_ARTICLE":
            section_title = task_result.get("section_title", "")
            section_index = task_result.get("section_index", 0)
            article_path = task_result.get("article_path", "")
            
            # スクリプト生成タスクを登録
            task_id = self.task_manager.register_task({
                "type": TaskType.API_CALL,
                "params": {
                    "api": "CLAUDE",
                    "operation": "GENERATE_SCRIPT",
                    "section_title": section_title,
                    "section_index": section_index,
                    "article_path": article_path
                }
            })
            
            logger.info(f"スクリプト生成タスクを登録しました: {task_id} - {section_title}")
            
            # ツイート生成タスクを登録
            task_id = self.task_manager.register_task({
                "type": TaskType.API_CALL,
                "params": {
                    "api": "CLAUDE",
                    "operation": "GENERATE_TWEETS",
                    "section_title": section_title,
                    "section_index": section_index,
                    "article_path": article_path
                }
            })
            
            logger.info(f"ツイート生成タスクを登録しました: {task_id} - {section_title}")
            
            # 台本JSON生成タスクを登録
            task_id = self.task_manager.register_task({
                "type": TaskType.API_CALL,
                "params": {
                    "api": "CLAUDE",
                    "operation": "GENERATE_SCRIPT_JSON",
                    "section_title": section_title,
                    "section_index": section_index,
                    "article_path": article_path
                }
            })
            
            logger.info(f"台本JSON生成タスクを登録しました: {task_id} - {section_title}")
        
        # ツイート生成結果からセクションコンテンツ結合タスクを登録
        elif "operation" in task_result and task_result["operation"] == "GENERATE_TWEETS":
            section_title = task_result.get("section_title", "")
            section_index = task_result.get("section_index", 0)
            
            # セクションコンテンツ結合タスクを登録
            task_id = self.task_manager.register_task({
                "type": TaskType.FILE_OPERATION,
                "params": {
                    "operation": "COMBINE_SECTION_CONTENTS",
                    "section_title": section_title,
                    "section_index": section_index
                }
            })
            
            logger.info(f"セクションコンテンツ結合タスクを登録しました: {task_id} - {section_title}")
        
        # セクションコンテンツ結合結果からチャプターコンテンツ結合タスクを登録
        elif "operation" in task_result and task_result["operation"] == "COMBINE_SECTION_CONTENTS":
            chapter_title = task_result.get("chapter_title", "")
            chapter_index = task_result.get("chapter_index", 0)
            
            # すべてのセクションが処理されたかチェック
            if self._all_sections_processed(chapter_index):
                # チャプターコンテンツ結合タスクを登録
                task_id = self.task_manager.register_task({
                    "type": TaskType.FILE_OPERATION,
                    "params": {
                        "operation": "COMBINE_CHAPTER_CONTENTS",
                        "chapter_title": chapter_title,
                        "chapter_index": chapter_index
                    }
                })
                
                logger.info(f"チャプターコンテンツ結合タスクを登録しました: {task_id} - {chapter_title}")
        
        # チャプターコンテンツ結合結果から構造ファイル作成タスクを登録
        elif "operation" in task_result and task_result["operation"] == "COMBINE_CHAPTER_CONTENTS":
            # すべてのチャプターが処理されたかチェック
            if self._all_chapters_processed():
                # 構造ファイル作成タスクを登録
                task_id = self.task_manager.register_task({
                    "type": TaskType.FILE_OPERATION,
                    "params": {
                        "operation": "CREATE_STRUCTURE_FILE"
                    }
                })
                
                logger.info(f"構造ファイル作成タスクを登録しました: {task_id}")
        
        # 構造ファイル作成結果から説明文作成タスクとサムネイル作成タスクを登録
        elif "operation" in task_result and task_result["operation"] == "CREATE_STRUCTURE_FILE":
            structure_path = task_result.get("structure_path", "")
            article_path = task_result.get("article_path", "")
            
            # 説明文作成タスクを登録
            task_id = self.task_manager.register_task({
                "type": TaskType.API_CALL,
                "params": {
                    "api": "CLAUDE",
                    "operation": "GENERATE_DESCRIPTION",
                    "structure_path": structure_path,
                    "article_path": article_path
                }
            })
            
            logger.info(f"説明文作成タスクを登録しました: {task_id}")
            
            # サムネイル作成タスクを登録 (説明文作成後に実行するため、直接は登録しない)
        
        # 説明文作成結果からサムネイル作成タスクを登録
        elif "operation" in task_result and task_result["operation"] == "GENERATE_DESCRIPTION":
            description_path = task_result.get("description_path", "")
            
            # サムネイル作成タスクを登録
            task_id = self.task_manager.register_task({
                "type": TaskType.API_CALL,
                "params": {
                    "api": "OPENAI",
                    "operation": "GENERATE_THUMBNAIL",
                    "description_path": description_path
                }
            })
            
            logger.info(f"サムネイル作成タスクを登録しました: {task_id}")
        
    def _execute_task(self, task: Dict) -> Any:
        """
        タスクを実行する

        Args:
            task: 実行するタスク情報

        Returns:
            Any: タスク実行結果
        """
        # タスクタイプに応じた処理を実行
        task_type = task["type"]
        params = task["params"]
        
        logger.debug(f"タスク実行開始: {task_type}, パラメータ: {params}")
        
        if task_type == "FILE_OPERATION":
            operation = params.get("operation")
            input_path = params.get("input_path")
            
            if operation == "SPLIT_CHAPTERS":
                from app.processors.content import ContentProcessor
                
                # ファイルを読み込む
                with open(input_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # チャプターに分割
                content_processor = ContentProcessor()
                chapters = content_processor.split_chapters(content)
                
                # 分割結果をログに出力
                logger.info(f"チャプター分割完了: {len(chapters)}個のチャプターを検出")
                for idx, chapter in enumerate(chapters, 1):
                    logger.info(f"チャプター{idx}: {chapter['title']}")
                
                return {
                    "success": True, 
                    "chapters": chapters, 
                    "input_path": input_path
                }
            
            elif operation == "SPLIT_SECTIONS":
                from app.processors.content import ContentProcessor
                
                chapter_content = params.get("chapter_content")
                
                # セクションに分割
                content_processor = ContentProcessor()
                sections = content_processor.split_sections(chapter_content)
                
                # 分割結果をログに出力
                logger.info(f"セクション分割完了: {len(sections)}個のセクションを検出")
                for idx, section in enumerate(sections, 1):
                    logger.info(f"セクション{idx}: {section['title']}")
                
                return {
                    "success": True, 
                    "sections": sections
                }
            
            else:
                logger.warning(f"未実装のファイル操作: {operation}")
                return {"success": False, "message": f"未実装のファイル操作: {operation}"}
                
        elif task_type == "API_CALL":
            api = params.get("api")
            
            if api == "CLAUDE":
                from app.clients.claude import ClaudeAPIClient
                
                # Claude APIを呼び出す処理
                operation = params.get("operation")
                section_content = params.get("section_content", "")
                section_title = params.get("section_title", "")
                section_index = params.get("section_index", 0)
                
                client = ClaudeAPIClient()
                
                if operation == "ANALYZE_STRUCTURE":
                    # セクション構造解析
                    result = client.analyze_structure(
                        section_content=section_content,
                        section_title=section_title,
                        section_index=section_index
                    )
                    
                    if result.get("success", False):
                        logger.info(f"セクション構造解析が完了しました: {section_title}")
                        return {
                            "success": True,
                            "operation": operation,
                            "section_title": section_title,
                            "section_index": section_index,
                            "analysis": result.get("analysis", "")
                        }
                    else:
                        logger.warning(f"セクション構造解析に失敗しました: {section_title}")
                        return {"success": False, "message": "セクション構造解析に失敗しました"}
                
                elif operation == "GENERATE_ARTICLE":
                    # 記事生成
                    from app.generators.article import ArticleGenerator
                    
                    section_title = params.get("section_title", "")
                    section_index = params.get("section_index", 0)
                    analysis = params.get("analysis", "")
                    
                    logger.info(f"記事生成を実行します: {section_title}")
                    
                    # ArticleGeneratorを使用して記事を生成
                    article_generator = ArticleGenerator()
                    article_content = article_generator.generate_article(
                        structure={"title": section_title, "analysis": analysis}
                    )
                    
                    # 出力ディレクトリを作成
                    import os
                    output_dir = os.path.join(self.config.get("output_dir", "output"), f"section_{section_index}")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # 記事を保存
                    article_path = os.path.join(output_dir, "article.md")
                    with open(article_path, "w", encoding="utf-8") as f:
                        f.write(article_content)
                    
                    logger.info(f"記事を生成しました: {article_path}")
                    
                    return {
                        "success": True,
                        "operation": operation,
                        "section_title": section_title,
                        "section_index": section_index,
                        "article_path": article_path
                    }
                
                elif operation == "GENERATE_SCRIPT":
                    # スクリプト生成
                    from app.generators.script import ScriptGenerator
                    
                    section_title = params.get("section_title", "")
                    section_index = params.get("section_index", 0)
                    article_path = params.get("article_path", "")
                    
                    # 記事内容を読み込む
                    with open(article_path, "r", encoding="utf-8") as f:
                        article_content = f.read()
                    
                    logger.info(f"スクリプト生成を実行します: {section_title}")
                    
                    # ScriptGeneratorを使用してスクリプトを生成
                    script_generator = ScriptGenerator()
                    script_content = script_generator.generate_script(
                        structure={"title": section_title},
                        article_content=article_content
                    )
                    
                    # 出力ディレクトリを取得
                    import os
                    output_dir = os.path.join(self.config.get("output_dir", "output"), f"section_{section_index}")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # スクリプトを保存
                    script_path = os.path.join(output_dir, "script.md")
                    with open(script_path, "w", encoding="utf-8") as f:
                        f.write(script_content)
                    
                    logger.info(f"スクリプトを生成しました: {script_path}")
                    
                    return {
                        "success": True,
                        "operation": operation,
                        "section_title": section_title,
                        "section_index": section_index,
                        "script_path": script_path
                    }
                
                elif operation == "GENERATE_SCRIPT_JSON":
                    # 台本JSON生成
                    from app.generators.script_json import ScriptJsonGenerator
                    
                    section_title = params.get("section_title", "")
                    section_index = params.get("section_index", 0)
                    article_path = params.get("article_path", "")
                    
                    # 記事内容を読み込む
                    with open(article_path, "r", encoding="utf-8") as f:
                        article_content = f.read()
                    
                    logger.info(f"台本JSON生成を実行します: {section_title}")
                    
                    # ScriptJsonGeneratorを使用して台本JSONを生成
                    script_json_generator = ScriptJsonGenerator()
                    script_json = script_json_generator.generate_script_json(
                        script_content=article_content  # 本来はscriptを使用するべき
                    )
                    
                    # 出力ディレクトリを取得
                    import os
                    output_dir = os.path.join(self.config.get("output_dir", "output"), f"section_{section_index}")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # 台本JSONを保存
                    script_json_path = os.path.join(output_dir, "script.json")
                    with open(script_json_path, "w", encoding="utf-8") as f:
                        import json
                        f.write(script_json)
                    
                    logger.info(f"台本JSONを生成しました: {script_json_path}")
                    
                    return {
                        "success": True,
                        "operation": operation,
                        "section_title": section_title,
                        "section_index": section_index,
                        "script_json_path": script_json_path
                    }
                
                elif operation == "GENERATE_TWEETS":
                    # ツイート生成
                    from app.generators.tweet import TweetGenerator
                    
                    section_title = params.get("section_title", "")
                    section_index = params.get("section_index", 0)
                    article_path = params.get("article_path", "")
                    
                    # 記事内容を読み込む
                    with open(article_path, "r", encoding="utf-8") as f:
                        article_content = f.read()
                    
                    logger.info(f"ツイート生成を実行します: {section_title}")
                    
                    # TweetGeneratorを使用してツイートを生成
                    tweet_generator = TweetGenerator()
                    tweets_data = tweet_generator.generate_tweets(
                        structure={"title": section_title},
                        article_content=article_content
                    )
                    
                    # CSVフォーマットに変換
                    import csv
                    from io import StringIO
                    
                    output = StringIO()
                    csv_writer = csv.writer(output)
                    csv_writer.writerow(["tweet_id", "content", "scheduled_date"])
                    
                    for i, tweet in enumerate(tweets_data, 1):
                        csv_writer.writerow([i, tweet, f"2025-{6+i:02d}-01"])
                    
                    tweets_content = output.getvalue()
                    
                    # 出力ディレクトリを取得
                    import os
                    output_dir = os.path.join(self.config.get("output_dir", "output"), f"section_{section_index}")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # ツイートCSVを保存
                    tweets_path = os.path.join(output_dir, "tweets.csv")
                    with open(tweets_path, "w", encoding="utf-8") as f:
                        f.write(tweets_content)
                    
                    logger.info(f"ツイートCSVを生成しました: {tweets_path}")
                    
                    return {
                        "success": True,
                        "operation": operation,
                        "section_title": section_title,
                        "section_index": section_index,
                        "tweets_path": tweets_path
                    }
                
                else:
                    logger.warning(f"未実装の操作: {operation}")
                    return {"success": False, "message": f"未実装の操作: {operation}"}
                
            elif api == "OPENAI":
                from app.clients.openai import OpenAIClient
                
                # OpenAI APIを呼び出す処理（実際にはここに実装が必要）
                logger.warning("OpenAI APIの呼び出しは未実装です")
                return {"success": False, "message": "OpenAI APIの呼び出しは未実装です"}
                
            else:
                logger.warning(f"未知のAPI: {api}")
                return {"success": False, "message": f"未知のAPI: {api}"}
            
        elif task_type == "GITHUB_OPERATION":
            from app.clients.github import GitHubClient
            
            # GitHub操作の実行
            operation = params.get("operation")
            section_title = params.get("section_title", "")
            section_index = params.get("section_index", 0)
            analysis = params.get("analysis", "")
            
            if operation == "PUSH_STRUCTURE":
                # ここではGitHub操作のシミュレーションを行う
                # 実際の実装ではGitHubAPIを使って変更をプッシュする
                
                # 出力ディレクトリを作成
                import os
                output_dir = os.path.join(self.config.get("output_dir", "output"), f"section_{section_index}")
                os.makedirs(output_dir, exist_ok=True)
                
                # 構造ファイルを保存
                structure_path = os.path.join(output_dir, "structure.json")
                import json
                with open(structure_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "title": section_title,
                        "index": section_index,
                        "analysis": analysis
                    }, f, ensure_ascii=False, indent=2)
                
                logger.info(f"構造ファイルを保存しました: {structure_path}")
                logger.info(f"GitHub操作（プッシュ）をシミュレーションしました: {section_title}")
                
                return {
                    "success": True,
                    "operation": operation,
                    "section_title": section_title,
                    "section_index": section_index,
                    "structure_path": structure_path
                }
            else:
                logger.warning(f"未実装のGitHub操作: {operation}")
                return {"success": False, "message": f"未実装のGitHub操作: {operation}"}
            
        elif task_type == "S3_OPERATION":
            from app.clients.s3 import S3Client
            
            # S3操作の実行
            operation = params.get("operation")
            
            s3_client = S3Client()
            
            if operation == "UPLOAD_IMAGE":
                # 画像のS3アップロード
                image_path = params.get("image_path", "")
                image_id = params.get("image_id", "")
                section_index = params.get("section_index", 0)
                
                # 画像データを読み込む
                with open(image_path, "rb") as f:
                    image_data = f.read()
                
                # S3にアップロード
                content_type = "image/png"  # 現状はPNGのみ対応
                key = f"images/section_{section_index}/{image_id}.png"
                
                public_url = s3_client.upload_file(
                    data=image_data,
                    key=key,
                    content_type=content_type
                )
                
                # 画像リンクをURL置換タスクを登録
                self.task_manager.register_task({
                    "type": TaskType.FILE_OPERATION,
                    "params": {
                        "operation": "REPLACE_IMAGE_LINKS",
                        "section_index": section_index,
                        "image_id": image_id,
                        "public_url": public_url
                    }
                })
                
                logger.info(f"画像をS3にアップロードしました: {image_id}, URL: {public_url}")
                
                return {
                    "success": True,
                    "operation": operation,
                    "image_id": image_id,
                    "public_url": public_url
                }
            
            elif operation == "UPLOAD_THUMBNAIL":
                # サムネイル画像のS3アップロード
                thumbnail_path = params.get("thumbnail_path", "")
                
                # 画像データを読み込む
                with open(thumbnail_path, "rb") as f:
                    thumbnail_data = f.read()
                
                # S3にアップロード
                content_type = "image/png"
                key = f"thumbnails/{os.path.basename(thumbnail_path)}"
                
                public_url = s3_client.upload_file(
                    data=thumbnail_data,
                    key=key,
                    content_type=content_type
                )
                
                logger.info(f"サムネイル画像をS3にアップロードしました: URL: {public_url}")
                
                return {
                    "success": True,
                    "operation": operation,
                    "thumbnail_path": thumbnail_path,
                    "public_url": public_url
                }
            
            else:
                logger.warning(f"未実装のS3操作: {operation}")
                return {"success": False, "message": f"未実装のS3操作: {operation}"}
            
        elif task_type == "IMAGE_PROCESSING":
            from app.processors.image import ImageProcessor
            
            # 画像処理の実行
            operation = params.get("operation")
            section_title = params.get("section_title", "")
            section_index = params.get("section_index", 0)
            
            image_processor = ImageProcessor()
            
            if operation == "ENCODE_IMAGES":
                # 画像のBase64エンコード処理
                content_path = params.get("content_path", "")
                
                # コンテンツを読み込む
                with open(content_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 画像を抽出してエンコード
                encoded_images = image_processor.extract_images(content)
                replaced_content = image_processor.replace_image_links(content, encoded_images)
                
                # 変換後のコンテンツを保存
                with open(content_path, "w", encoding="utf-8") as f:
                    f.write(replaced_content)
                
                logger.info(f"画像のBase64エンコード処理が完了しました: {section_title}")
                
                return {
                    "success": True,
                    "operation": operation,
                    "section_title": section_title,
                    "section_index": section_index,
                    "content_path": content_path,
                    "encoded_images": encoded_images
                }
            
            elif operation == "PROCESS_ARTICLE_IMAGES":
                # 記事内の画像処理
                article_path = params.get("article_path", "")
                
                # 記事を読み込む
                with open(article_path, "r", encoding="utf-8") as f:
                    article_content = f.read()
                
                # 画像タイプを判定して適切に処理
                image_types = image_processor.detect_image_types(article_content)
                processed_images = {}
                
                for image_type, images in image_types.items():
                    if image_type == "svg":
                        for image in images:
                            png_data = image_processor.process_svg(image["content"])
                            processed_images[image["id"]] = {
                                "data": png_data,
                                "type": "png"
                            }
                    elif image_type == "drawio":
                        for image in images:
                            png_data = image_processor.process_drawio(image["content"])
                            processed_images[image["id"]] = {
                                "data": png_data,
                                "type": "png"
                            }
                    elif image_type == "mermaid":
                        for image in images:
                            png_data = image_processor.process_mermaid(image["content"])
                            processed_images[image["id"]] = {
                                "data": png_data,
                                "type": "png"
                            }
                
                # 画像をimagesフォルダに保存
                import os
                output_dir = os.path.join(self.config.get("output_dir", "output"), f"section_{section_index}", "images")
                os.makedirs(output_dir, exist_ok=True)
                
                image_map = {}
                for image_id, image_data in processed_images.items():
                    image_path = os.path.join(output_dir, f"{image_id}.png")
                    with open(image_path, "wb") as f:
                        f.write(image_data["data"])
                    image_map[image_id] = image_path
                
                # S3アップロードタスクの登録
                for image_id, image_path in image_map.items():
                    self.task_manager.register_task({
                        "type": TaskType.S3_OPERATION,
                        "params": {
                            "operation": "UPLOAD_IMAGE",
                            "image_path": image_path,
                            "image_id": image_id,
                            "section_index": section_index
                        }
                    })
                
                logger.info(f"記事内画像処理が完了しました: {section_title}, 処理画像数: {len(processed_images)}")
                
                return {
                    "success": True,
                    "operation": operation,
                    "section_title": section_title,
                    "section_index": section_index,
                    "article_path": article_path,
                    "image_map": image_map
                }
            
            else:
                logger.warning(f"未実装の画像処理操作: {operation}")
                return {"success": False, "message": f"未実装の画像処理操作: {operation}"}
            
        else:
            raise ValueError(f"未知のタスクタイプ: {task_type}") 

    def _all_sections_processed(self, chapter_index: int) -> bool:
        """
        特定のチャプターの全セクションが処理されたかどうかを確認する

        Args:
            chapter_index: チャプターインデックス

        Returns:
            bool: 全セクションが処理された場合はTrue、それ以外はFalse
        """
        # この実装は単純化されています。実際には状態管理が必要です。
        # タスク管理システムの実装に依存します。
        all_tasks = self.task_manager.get_all_tasks()
        
        # 該当チャプターのセクション数を取得
        section_count = 0
        for task in all_tasks:
            if task["type"] == TaskType.FILE_OPERATION and \
                task["params"].get("operation") == "SPLIT_SECTIONS" and \
                task["params"].get("chapter_index") == chapter_index:
                # 結果からセクション数を取得
                if task.get("result") and "sections" in task["result"]:
                    section_count = len(task["result"]["sections"])
                    break
        
        # 結合処理されたセクション数を取得
        processed_count = 0
        for task in all_tasks:
            if task["type"] == TaskType.FILE_OPERATION and \
                task["params"].get("operation") == "COMBINE_SECTION_CONTENTS" and \
                task["params"].get("chapter_index") == chapter_index and \
                task["status"] == "COMPLETED":
                processed_count += 1
        
        return processed_count >= section_count
    
    def _all_chapters_processed(self) -> bool:
        """
        全てのチャプターが処理されたかどうかを確認する

        Returns:
            bool: 全チャプターが処理された場合はTrue、それ以外はFalse
        """
        # この実装は単純化されています。実際には状態管理が必要です。
        # タスク管理システムの実装に依存します。
        all_tasks = self.task_manager.get_all_tasks()
        
        # チャプター数を取得
        chapter_count = 0
        for task in all_tasks:
            if task["type"] == TaskType.FILE_OPERATION and \
                task["params"].get("operation") == "SPLIT_CHAPTERS":
                # 結果からチャプター数を取得
                if task.get("result") and "chapters" in task["result"]:
                    chapter_count = len(task["result"]["chapters"])
                    break
        
        # 結合処理されたチャプター数を取得
        processed_count = 0
        for task in all_tasks:
            if task["type"] == TaskType.FILE_OPERATION and \
                task["params"].get("operation") == "COMBINE_CHAPTER_CONTENTS" and \
                task["status"] == "COMPLETED":
                processed_count += 1
        
        return processed_count >= chapter_count 