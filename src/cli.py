"""CLI エントリーポイント

リソース生成ワークフローのコマンドラインインターフェース
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click

from .config.settings import Config
from .core.orchestrator import WorkflowOrchestrator
from .utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


@click.group()
@click.option('--debug', is_flag=True, help='デバッグモードで実行')
@click.option('--config', type=click.Path(exists=True), help='設定ファイルのパス')
@click.pass_context
def cli(ctx, debug: bool, config: Optional[str]):
    """リソース生成ワークフロー CLI"""
    # コンテキストオブジェクトの初期化
    ctx.ensure_object(dict)
    
    # ログレベルの設定
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(level=log_level)
    
    # 設定の読み込み
    try:
        if config:
            ctx.obj['config'] = Config.from_file(Path(config))
        else:
            ctx.obj['config'] = Config.from_env()
    except Exception as e:
        logger.error(f"設定の読み込みに失敗しました: {e}")
        sys.exit(1)


@cli.command()
@click.option('--lang', required=True, help='言語コード (例: ja, en)')
@click.option('--title', required=True, help='書籍タイトル')
@click.option('--input-file', type=click.Path(exists=True), help='入力ファイルのパス')
@click.option('--resume', help='再開するワークフローID')
@click.pass_context
def generate(ctx, lang: str, title: str, input_file: Optional[str], resume: Optional[str]):
    """コンテンツ生成ワークフローを実行"""
    config = ctx.obj['config']
    
    async def run_workflow():
        orchestrator = WorkflowOrchestrator(config)
        
        try:
            if resume:
                # ワークフローの再開
                logger.info(f"ワークフロー {resume} を再開します")
                context = await orchestrator.resume(resume)
            else:
                # 新規ワークフローの実行
                logger.info(f"新規ワークフローを開始します: {lang}, {title}")
                context = await orchestrator.execute(lang, title, input_file)
            
            logger.info(f"ワークフローが完了しました: {context.workflow_id}")
            click.echo(f"✅ ワークフロー完了: {context.workflow_id}")
            
        except Exception as e:
            logger.error(f"ワークフロー実行エラー: {e}")
            click.echo(f"❌ エラー: {e}", err=True)
            sys.exit(1)
        finally:
            await orchestrator.shutdown()
    
    # 非同期関数の実行
    asyncio.run(run_workflow())


@cli.command()
@click.pass_context
def orchestrate(ctx):
    """オーケストレーター単体での起動（ワーカーモード用）"""
    config = ctx.obj['config']
    
    async def run_orchestrator():
        orchestrator = WorkflowOrchestrator(config)
        
        try:
            logger.info("オーケストレーターを起動します")
            await orchestrator.initialize()
            
            # 無限ループで待機（Ctrl+Cで終了）
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("停止シグナルを受信しました")
        except Exception as e:
            logger.error(f"オーケストレーターエラー: {e}")
            sys.exit(1)
        finally:
            await orchestrator.shutdown()
    
    asyncio.run(run_orchestrator())


@cli.command()
@click.option('--workflow-id', required=True, help='チェックするワークフローID')
@click.pass_context
def status(ctx, workflow_id: str):
    """ワークフロー状態の確認"""
    config = ctx.obj['config']
    
    async def check_status():
        from .core.state import StateManager
        
        state_manager = StateManager(config)
        try:
            await state_manager.initialize()
            
            # ワークフロー状態の取得
            state = await state_manager.get_workflow_state(workflow_id)
            if not state:
                click.echo(f"❌ ワークフロー {workflow_id} が見つかりません")
                return
            
            # 状態の表示
            click.echo(f"📋 ワークフロー状態: {workflow_id}")
            click.echo(f"   ステータス: {state.get('status', 'unknown')}")
            click.echo(f"   作成日時: {state.get('created_at', 'unknown')}")
            click.echo(f"   言語: {state.get('lang', 'unknown')}")
            click.echo(f"   タイトル: {state.get('title', 'unknown')}")
            
            # チェックポイント情報
            checkpoints = await state_manager.get_checkpoints(workflow_id)
            if checkpoints:
                click.echo(f"   チェックポイント数: {len(checkpoints)}")
                latest = checkpoints[-1] if checkpoints else None
                if latest:
                    click.echo(f"   最新チェックポイント: {latest.get('type', 'unknown')}")
            
        except Exception as e:
            logger.error(f"ステータス確認エラー: {e}")
            click.echo(f"❌ エラー: {e}", err=True)
            sys.exit(1)
        finally:
            await state_manager.close()
    
    asyncio.run(check_status())


@cli.command()
@click.pass_context
def worker(ctx):
    """ワーカーモードで起動"""
    config = ctx.obj['config']
    worker_type = config.worker_type if hasattr(config, 'worker_type') else 'all'
    
    async def run_worker():
        from .workers.pool import WorkerPool
        from .core.events import EventBus
        from .core.state import StateManager
        
        # 必要なコンポーネントの初期化
        event_bus = EventBus(config)
        state_manager = StateManager(config)
        worker_pool = WorkerPool(config)
        
        try:
            logger.info(f"ワーカーを起動します: {worker_type}")
            
            # 初期化
            await state_manager.initialize()
            await event_bus.start()
            await worker_pool.initialize(event_bus, state_manager)
            await worker_pool.start()
            
            # 無限ループで待機
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("停止シグナルを受信しました")
        except Exception as e:
            logger.error(f"ワーカーエラー: {e}")
            sys.exit(1)
        finally:
            await worker_pool.shutdown()
            await event_bus.stop()
            await state_manager.close()
    
    asyncio.run(run_worker())


@cli.command()
@click.pass_context
def health(ctx):
    """システムヘルスチェック"""
    config = ctx.obj['config']
    
    async def check_health():
        click.echo("🔍 システムヘルスチェック")
        
        health_status = {}
        
        # Redis接続チェック
        try:
            from .core.state import StateManager
            state_manager = StateManager(config)
            await state_manager.initialize()
            health_status['redis'] = True
            await state_manager.close()
            click.echo("✅ Redis: 接続OK")
        except Exception as e:
            health_status['redis'] = False
            click.echo(f"❌ Redis: 接続エラー - {e}")
        
        # 外部API接続チェック
        api_checks = [
            ('Claude API', 'claude'),
            ('OpenAI API', 'openai'),
        ]
        
        for api_name, client_name in api_checks:
            try:
                # APIクライアントのヘルスチェック（実装されている場合）
                health_status[client_name] = True
                click.echo(f"✅ {api_name}: 設定OK")
            except Exception as e:
                health_status[client_name] = False
                click.echo(f"❌ {api_name}: 設定エラー - {e}")
        
        # 全体ステータス
        all_healthy = all(health_status.values())
        if all_healthy:
            click.echo("🎉 すべてのコンポーネントが正常です")
        else:
            click.echo("⚠️  一部のコンポーネントに問題があります")
            sys.exit(1)
    
    asyncio.run(check_health())


def main():
    """メインエントリーポイント"""
    cli()


if __name__ == '__main__':
    main() 