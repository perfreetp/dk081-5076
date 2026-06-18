"""
分派路径验收脚本

覆盖三种差评提交场景，验证工单与分派结果是否走了期望的分派路径：
  场景A：只传事项名称（营业执照办理）        期望 -> item_mapping_by_name -> 市场监管窗口 WIN003
  场景B：同时传编码+名称（101/不动产登记）   期望 -> item_mapping_by_code  -> 不动产登记窗口 WIN002
  场景C：名称完全陌生（外星人登记认证）      期望 -> problem_type / default_supervision -> 督查室或问题类型兜底

使用方式：
  1. 先初始化数据库：python init_db.py
  2. 直接运行本脚本：python test_dispatch_scenarios.py
     （也可在服务启动后用 HTTP 调用 /api/evaluations/receive 复现同样结果）
"""
import sys
import uuid
from datetime import datetime

sys.path.insert(0, '.')

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.config.database import SessionLocal
from app.core.enums import DataSource, EvaluationLevel
from app.schemas.evaluation import EvaluationCreate
from app.services.collection_service import CollectionService


PATH_DESC = {
    "item_mapping_by_code": "事项编码命中事项映射",
    "item_mapping_by_name": "事项名称精确命中事项映射",
    "item_mapping_by_keyword": "事项名称关键词命中事项映射",
    "dept_name_match": "事项名称命中部门名称",
    "problem_type": "按问题类型兜底",
    "dept_code_match": "按评价部门编码分派",
    "default_supervision": "兜底至营商环境督查室",
}


def build_eval(evaluation_no, source, level, content, item_code=None, item_name=None,
               citizen_phone=None, dept_code=None):
    return EvaluationCreate(
        evaluation_no=evaluation_no,
        source=source,
        level=level,
        score=1.0,
        citizen_name="验收测试群众",
        citizen_phone=citizen_phone or f"138{uuid.uuid4().hex[:8]}",
        item_code=item_code,
        item_name=item_name,
        dept_code=dept_code,
        content=content,
        happen_time=datetime.now(),
        evaluate_time=datetime.now()
    )


def run_scenario(db, title, eval_data, expected_path_hint):
    print("\n" + "=" * 80)
    print(f"【{title}】")
    print(f"  输入: item_code={eval_data.item_code!r}, item_name={eval_data.item_name!r}")
    print(f"  期望路径提示: {expected_path_hint}")
    print("-" * 80)

    service = CollectionService(db)
    evaluation = service.receive_evaluation(eval_data, operator="acceptance_test")
    detail = service.get_evaluation_with_detail(evaluation.id)

    if not detail:
        print("  [FAIL] 评价详情获取失败")
        return

    ticket_info = detail.get("ticket_info")
    if not ticket_info:
        print("  [FAIL] 未生成工单（ticket_info 为空）")
        return

    ticket_no = ticket_info.get("ticket_no")
    status = ticket_info.get("status")
    dept_code = ticket_info.get("assigned_dept_code")
    dept_name = ticket_info.get("assigned_dept_name")
    dept_type = ticket_info.get("assigned_dept_type")
    dispatch_path = ticket_info.get("dispatch_path")
    latest = ticket_info.get("latest_assignment") or {}

    print(f"  工单号        : {ticket_no}")
    print(f"  工单状态      : {status}")
    print(f"  责任部门      : {dept_code} / {dept_name}（{dept_type}）")
    print(f"  分派路径      : {dispatch_path}  ->  {PATH_DESC.get(dispatch_path, '未知')}")
    print(f"  最新分派记录  :")
    print(f"     - 分派时间 : {latest.get('assign_time')}")
    print(f"     - 截止时间 : {latest.get('deadline')}")
    print(f"     - 分派说明 : {latest.get('assign_reason')}")
    print(f"     - dispatch_path: {latest.get('dispatch_path')}")

    if dispatch_path and expected_path_hint in dispatch_path:
        print(f"  [OK] 路径符合预期（包含 {expected_path_hint}）")
    else:
        print(f"  [FAIL] 路径不符合预期，期望包含 {expected_path_hint}，实际 {dispatch_path}")


def main():
    print("=" * 80)
    print("分派路径验收脚本启动")
    print("=" * 80)
    print("说明：本脚本直接调用服务层，模拟 /api/evaluations/receive 的完整流程。")
    print("如需 HTTP 验收，启动服务后用相同入参 POST /api/evaluations/receive 即可。")

    db = SessionLocal()
    try:
        run_scenario(
            db,
            title="场景A：只传事项名称（营业执照办理）",
            eval_data=build_eval(
                evaluation_no=f"EVA-A-{uuid.uuid4().hex[:6].upper()}",
                source=DataSource.HALL,
                level=EvaluationLevel.POOR,
                content="窗口工作人员态度很差，办理营业执照的时候一直不耐烦",
                item_code=None,
                item_name="营业执照办理"
            ),
            expected_path_hint="item_mapping"
        )

        run_scenario(
            db,
            title="场景B：同时传编码+名称（101/不动产登记）",
            eval_data=build_eval(
                evaluation_no=f"EVA-B-{uuid.uuid4().hex[:6].upper()}",
                source=DataSource.APP,
                level=EvaluationLevel.VERY_POOR,
                content="不动产登记流程太慢，等了好几个小时都没办好",
                item_code="101",
                item_name="不动产登记"
            ),
            expected_path_hint="item_mapping_by_code"
        )

        run_scenario(
            db,
            title="场景C：名称完全陌生（星际移民审批）",
            eval_data=build_eval(
                evaluation_no=f"EVA-C-{uuid.uuid4().hex[:6].upper()}",
                source=DataSource.HOTLINE_12345,
                level=EvaluationLevel.POOR,
                content="星际移民审批这个事项没人受理，部门之间互相推诿",
                item_code=None,
                item_name="星际移民审批"
            ),
            expected_path_hint=""
        )

        print("\n" + "=" * 80)
        print("验收完成。请核对每条工单的 分派路径 字段是否符合业务预期。")
        print("=" * 80)
    finally:
        db.close()


if __name__ == "__main__":
    main()
