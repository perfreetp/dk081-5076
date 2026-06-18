from datetime import datetime
import logging
from typing import Optional

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    IntervalTrigger = None
    CronTrigger = None

from app.config.database import SessionLocal
from app.services.reminder_service import ReminderService
from app.services.archive_service import ArchiveService

logger = logging.getLogger(__name__)

scheduler = None
if APSCHEDULER_AVAILABLE:
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def reminder_check_job():
    logger.info(f"执行超时催办检查任务: {datetime.now()}")
    db = SessionLocal()
    try:
        service = ReminderService(db)
        reminders = service.check_and_create_reminders()
        logger.info(f"超时催办检查完成，生成{len(reminders)}条催办记录")
    except Exception as e:
        logger.error(f"超时催办检查任务执行失败: {e}", exc_info=True)
    finally:
        db.close()


def auto_archive_job():
    logger.info(f"执行自动归档任务: {datetime.now()}")
    db = SessionLocal()
    try:
        service = ArchiveService(db)
        archives = service.auto_archive_completed(days=30)
        logger.info(f"自动归档任务完成，归档{len(archives)}条记录")
    except Exception as e:
        logger.error(f"自动归档任务执行失败: {e}", exc_info=True)
    finally:
        db.close()


def overdue_statistics_job():
    logger.info(f"执行超时统计任务: {datetime.now()}")
    db = SessionLocal()
    try:
        service = ReminderService(db)
        overdue_tickets = service.get_overdue_tickets()
        logger.info(f"超时统计完成，当前共{len(overdue_tickets)}条超时工单")
        for ticket in overdue_tickets:
            logger.warning(
                f"超时工单: {ticket.ticket_no}, "
                f"状态: {ticket.status}, "
                f"责任部门: {ticket.assigned_dept_name}, "
                f"截止时间: {ticket.deadline_time}"
            )
    except Exception as e:
        logger.error(f"超时统计任务执行失败: {e}", exc_info=True)
    finally:
        db.close()


def start_scheduler():
    global scheduler
    if APSCHEDULER_AVAILABLE and scheduler:
        scheduler.add_job(
            reminder_check_job,
            trigger=IntervalTrigger(hours=1),
            id="reminder_check",
            name="超时催办检查",
            replace_existing=True
        )

        scheduler.add_job(
            auto_archive_job,
            trigger=CronTrigger(hour=2, minute=0),
            id="auto_archive",
            name="自动归档",
            replace_existing=True
        )

        scheduler.add_job(
            overdue_statistics_job,
            trigger=CronTrigger(hour=8, minute=30),
            id="overdue_statistics",
            name="每日超时统计",
            replace_existing=True
        )

        scheduler.start()
        logger.info("定时任务调度器已启动")
        for job in scheduler.get_jobs():
            logger.info(f"已注册任务: {job.name} - {job.id}")
    else:
        logger.warning("APScheduler未安装，定时任务功能不可用。请安装APScheduler后重启服务。")


def stop_scheduler():
    global scheduler
    if APSCHEDULER_AVAILABLE and scheduler:
        scheduler.shutdown()
        logger.info("定时任务调度器已停止")
