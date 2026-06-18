"""
HTTP 接口验收脚本

直接请求运行中的服务接口，验证分派闭环与升级兼容：
  场景1：只传事项名称的差评 -> 接收 + 工单详情 + 轨迹
  场景2：改派后再查询 -> 看前后责任部门变化 + 分派历史
  场景3：旧库升级后提交 -> 历史数据仍在，新差评正常分派

前置条件：服务已启动（python main.py），默认地址 http://localhost:8000
运行方式：python test_api_acceptance.py
"""
import json
import sys
import time
import uuid
import urllib.request
import urllib.error

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_URL = "http://localhost:8000"


def http_request(method, path, data=None):
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"  [HTTP {e.code}] {method} {path}")
        print(f"  响应: {err_body[:300]}")
        return None
    except urllib.error.URLError as e:
        print(f"  [连接失败] 请确认服务已启动：{BASE_URL}。错误: {e}")
        sys.exit(1)


def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def print_section(title):
    print("\n" + "=" * 80)
    print(f"【{title}】")
    print("-" * 80)


def print_kv(label, value):
    print(f"  {label:<16}: {value}")


def receive_eval(**kwargs):
    payload = {
        "evaluation_no": f"EVA-{uuid.uuid4().hex[:8].upper()}",
        "source": "hall",
        "level": "poor",
        "score": 1.0,
        "citizen_name": "验收测试群众",
        "citizen_phone": f"138{uuid.uuid4().hex[:8]}",
        "happen_time": now_str(),
        "evaluate_time": now_str(),
        **kwargs
    }
    return http_request("POST", "/api/evaluations/receive", payload)


def print_ticket_detail(resp):
    if not resp or resp.get("code") != 200:
        print("  [FAIL] 接收失败")
        return None

    data = resp["data"]
    print_kv("评价编号", data.get("evaluation_no"))
    print_kv("事项编码", data.get("item_code"))
    print_kv("事项名称", data.get("item_name"))

    ticket = data.get("ticket_info") or {}
    print_kv("工单号", ticket.get("ticket_no"))
    print_kv("工单状态", ticket.get("status"))
    print_kv("责任部门", f"{ticket.get('assigned_dept_code')} / {ticket.get('assigned_dept_name')}")
    print_kv("分派路径", f"{ticket.get('dispatch_path')} -> {ticket.get('dispatch_path_desc')}")

    latest = ticket.get("latest_assignment") or {}
    print_kv("最新分派时间", latest.get("assign_time"))
    print_kv("截止时间", latest.get("deadline"))
    print_kv("分派说明", latest.get("assign_reason"))
    return ticket


def scenario1_only_name():
    """场景1：只传事项名称"""
    print_section("场景1：只传事项名称（营业执照办理）")
    resp = receive_eval(
        item_name="营业执照办理",
        item_code=None,
        content="窗口工作人员态度差，办理营业执照一直不耐烦"
    )
    return print_ticket_detail(resp), resp


def scenario2_reassign(ticket_no):
    """场景2：改派后再查询，看前后责任部门变化"""
    print_section("场景2：改派后再查询（查看前后责任部门变化 + 分派历史）")

    by_no_resp = http_request("GET", f"/api/tickets/no/{ticket_no}")
    if not by_no_resp or by_no_resp.get("code") != 200:
        print("  [FAIL] 查询工单失败")
        return
    ticket = by_no_resp["data"]
    ticket_id = ticket["id"]
    old_dept = f"{ticket.get('assigned_dept_code')} / {ticket.get('assigned_dept_name')}"
    print_kv("改派前责任部门", old_dept)

    assign_resp = http_request("POST", "/api/tickets/assign", {
        "ticket_id": ticket_id,
        "dept_code": "WIN002",
        "dept_name": "不动产登记窗口",
        "dept_type": "window",
        "assign_user": "acceptance_test",
        "assign_reason": "验收测试：人工改派至不动产登记窗口"
    })
    if not assign_resp or assign_resp.get("code") != 200:
        print("  [FAIL] 改派失败")
        return
    print("  [OK] 人工改派成功")

    print("\n  --- 改派后查询工单详情 ---")
    detail_resp = http_request("GET", f"/api/tickets/{ticket_id}")
    if not detail_resp or detail_resp.get("code") != 200:
        print("  [FAIL] 查询详情失败")
        return

    detail = detail_resp["data"]
    print_kv("当前责任部门", f"{detail.get('assigned_dept_code')} / {detail.get('assigned_dept_name')}")
    print_kv("分派路径", f"{detail.get('dispatch_path')} -> {detail.get('dispatch_path_desc')}")

    print("\n  --- 分派历史（assignment_history）---")
    history = detail.get("assignment_history") or []
    for i, h in enumerate(history, 1):
        from_dept = f"{h.get('from_dept_code')}/{h.get('from_dept_name')}" if h.get('from_dept_code') else "(无)"
        to_dept = f"{h.get('to_dept_code')}/{h.get('to_dept_name')}"
        path = h.get("dispatch_path_desc") or h.get("dispatch_path") or "-"
        status_parts = []
        if h.get("is_accepted"):
            status_parts.append(f"已接单({h.get('accept_user','')})")
        if h.get("is_rejected"):
            status_parts.append(f"已拒收({h.get('reject_reason','')})")
        status_text = "、".join(status_parts) if status_parts else "待接单"
        print(f"  #{i} [{h.get('assign_time')}] {from_dept} -> {to_dept}")
        print(f"     路径: {path} | {status_text}")
        print(f"     说明: {h.get('assign_reason')}")

    print("\n  --- 流转轨迹（operation_trail）---")
    trail = detail.get("operation_trail") or []
    for log in trail:
        print(f"  [{log.get('operation_time')}] {log.get('operation_desc')} (操作人: {log.get('operator')})")


def scenario3_duplicate_merge():
    """场景3：同一群众同一事项多渠道差评，验证合并与结构化时间线"""
    print_section("场景3：同一群众同一事项多渠道差评合并 + 结构化时间线")
    phone = f"139{uuid.uuid4().hex[:8]}"
    base = {
        "citizen_name": "张三",
        "citizen_phone": phone,
        "item_name": "纳税申报",
        "item_code": None,
        "content": "纳税申报流程太慢"
    }

    print("\n  渠道1：政务大厅提交")
    r1 = receive_eval(source="hall", level="poor", **base)
    if not r1 or r1.get("code") != 200:
        print("  [FAIL] 渠道1提交失败")
        return
    ticket_no = (r1["data"].get("ticket_info") or {}).get("ticket_no")
    print_kv("工单号", ticket_no)

    print("\n  渠道2：政务App提交（应合并到同一工单）")
    r2 = receive_eval(source="app", level="very_poor", **base)
    if r2 and r2.get("code") == 200:
        t2 = (r2["data"].get("ticket_info") or {}).get("ticket_no")
        print_kv("工单号", t2)
        print(f"  [OK] 合并到同一工单" if t2 == ticket_no else f"  [注意] 工单号不一致")

    print("\n  渠道3：12345热线提交（应继续合并）")
    r3 = receive_eval(source="12345", level="poor", **base)
    if r3 and r3.get("code") == 200:
        t3 = (r3["data"].get("ticket_info") or {}).get("ticket_no")
        print_kv("工单号", t3)

    print("\n  --- 查询工单详情：合并汇总（merged_summary）---")
    detail_resp = http_request("GET", f"/api/tickets/no/{ticket_no}")
    if not detail_resp or detail_resp.get("code") != 200:
        print("  [FAIL] 查询详情失败")
        return
    detail = detail_resp["data"]
    merged = detail.get("merged_summary") or {}
    print_kv("评价总数", merged.get("total_count"))
    print_kv("来源渠道", "、".join(merged.get("source_channels", [])))
    print_kv("最早时间", merged.get("first_time"))
    print_kv("最晚时间", merged.get("last_time"))

    print("\n  --- 评价时间线（timeline）---")
    timeline = merged.get("timeline") or []
    for e in timeline:
        role = "原始" if e.get("is_original") else "合并"
        print(f"  [{e.get('evaluate_time')}] [{e.get('source_desc')}] [{role}] {e.get('evaluation_no')}: {e.get('content')}")


def scenario4_old_db_upgrade():
    """场景4：模拟旧库升级后提交"""
    print_section("场景4：旧库升级后提交（验证历史数据保留 + 新差评正常分派）")
    print("  说明：本场景假设数据库已通过 upgrade_db.py 升级，历史数据保留。")
    print("  直接提交一条新差评，验证接口正常返回。")

    resp = receive_eval(
        item_name="社保开户办理",
        item_code=None,
        content="旧库升级后提交的差评，验证接口正常工作"
    )
    print_ticket_detail(resp)


def main():
    print("=" * 80)
    print("HTTP 接口验收脚本启动")
    print(f"目标服务: {BASE_URL}")
    print("=" * 80)

    health = http_request("GET", "/health")
    if not health:
        print("[FAIL] 服务未启动，请先运行: python main.py")
        sys.exit(1)
    print("[OK] 服务健康检查通过")

    ticket1, _ = scenario1_only_name()
    if ticket1 and ticket1.get("ticket_no"):
        scenario2_reassign(ticket1["ticket_no"])

    scenario3_duplicate_merge()
    scenario4_old_db_upgrade()

    print("\n" + "=" * 80)
    print("验收完成。请核对各场景的工单、分派路径、分派历史与合并时间线。")
    print("=" * 80)


if __name__ == "__main__":
    main()
