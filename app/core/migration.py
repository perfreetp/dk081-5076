"""
数据库自动迁移模块

用于旧库平滑升级：检测并补齐新增列，不删除任何历史数据。
支持 SQLite / PostgreSQL，通过原生 ALTER TABLE ADD COLUMN 实现。
"""
import logging
from sqlalchemy import inspect, text

from app.config.database import engine, Base

logger = logging.getLogger(__name__)


MIGRATIONS = {
    "tickets": {
        "dept_code": "VARCHAR(64)",
        "dept_name": "VARCHAR(255)",
    },
    "assignments": {
        "dispatch_path": "VARCHAR(64)",
    },
    "archives": {
        "assignments_snapshot": "JSON",
    },
}


def _normalize_col_type(db_type: str) -> str:
    return db_type.upper().split("(")[0].strip()


def run_migration() -> dict:
    """
    执行自动迁移：检查每张表是否缺少新增列，缺失则通过 ALTER TABLE 补齐。
    返回迁移摘要 dict: {"added": [...], "skipped": [...]}
    """
    inspector = inspect(engine)
    summary = {"added": [], "skipped": []}

    existing_tables = inspector.get_table_names()

    for table_name, columns in MIGRATIONS.items():
        if table_name not in existing_tables:
            logger.info(f"迁移跳过：表 {table_name} 尚未创建（将由 create_all 处理）")
            continue

        existing_columns = {col["name"]: col for col in inspector.get_columns(table_name)}

        for col_name, col_type in columns.items():
            if col_name in existing_columns:
                summary["skipped"].append(f"{table_name}.{col_name}")
                continue

            if engine.dialect.name == "sqlite":
                ddl_type = _sqlite_type(col_type)
                default_expr = ""
            else:
                ddl_type = col_type
                default_expr = ""

            sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {ddl_type}{default_expr}'
            try:
                with engine.begin() as conn:
                    conn.execute(text(sql))
                logger.info(f"迁移成功：已新增列 {table_name}.{col_name} ({ddl_type})")
                summary["added"].append(f"{table_name}.{col_name}")
            except Exception as e:
                logger.warning(f"迁移失败 {table_name}.{col_name}: {e}")
                summary["skipped"].append(f"{table_name}.{col_name}(错误:{e})")

    if summary["added"]:
        logger.info(f"本次迁移新增列 {len(summary['added'])} 个：{summary['added']}")
    else:
        logger.info("数据库结构检查完成，无需迁移新增列")

    return summary


def _sqlite_type(col_type: str) -> str:
    t = _normalize_col_type(col_type)
    if t == "JSON":
        return "JSON"
    return col_type


def ensure_schema():
    """确保所有表存在并完成迁移，供应用启动时调用。"""
    Base.metadata.create_all(bind=engine)
    return run_migration()
