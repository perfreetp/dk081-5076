"""
数据库升级脚本

用于旧库平滑升级到新版本，不删除任何历史数据：
  - 自动检测并补齐新增列（tickets.dept_code/dept_name、assignments.dispatch_path、archives.assignments_snapshot）
  - 创建缺失的表
  - 历史评价和工单完整保留

使用方式：
  python upgrade_db.py
"""
import sys

sys.path.insert(0, '.')

from app.core.migration import ensure_schema


def main():
    print("=" * 60)
    print("数据库升级脚本（旧库平滑升级，不删除历史数据）")
    print("=" * 60)

    summary = ensure_schema()

    print()
    if summary["added"]:
        print(f"[新增列] 共 {len(summary['added'])} 个：")
        for item in summary["added"]:
            print(f"  + {item}")
    else:
        print("[新增列] 无，数据库已是最新结构")

    if summary["skipped"]:
        print(f"\n[已存在/跳过] 共 {len(summary['skipped'])} 个：")
        for item in summary["skipped"]:
            print(f"  - {item}")

    print()
    print("升级完成。历史评价、工单、分派记录均已保留，可继续接收差评。")


if __name__ == "__main__":
    main()
