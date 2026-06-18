from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.core.models import Ticket, Assignment, ItemMapping, Department
from app.core.enums import (
    DepartmentType, TicketStatus, ProblemType, UrgencyLevel
)
from app.config.settings import settings
from app.schemas.ticket import TicketAssign
from app.services.trail_service import TrailService

logger = logging.getLogger(__name__)


class DispatchService:
    def __init__(self, db: Session):
        self.db = db
        self.trail_service = TrailService(db)

    def auto_dispatch(self, ticket: Ticket) -> Optional[Assignment]:
        dept_code = None
        dept_name = None
        dept_type = None
        dispatch_path = "default_supervision"
        match_detail = ""

        mapping = None
        if ticket.item_code:
            mapping = self.db.query(ItemMapping).filter(
                ItemMapping.item_code == ticket.item_code,
                ItemMapping.is_active == True
            ).first()
            if mapping:
                dispatch_path = "item_mapping_by_code"
                match_detail = f"事项编码[{ticket.item_code}]命中事项映射"

        if not mapping and ticket.item_name:
            mapping = self.db.query(ItemMapping).filter(
                ItemMapping.item_name == ticket.item_name,
                ItemMapping.is_active == True
            ).first()
            if mapping:
                dispatch_path = "item_mapping_by_name"
                match_detail = f"事项名称[{ticket.item_name}]精确命中事项映射"

        if not mapping and ticket.item_name:
            keyword_match = self._match_item_mapping_by_keywords(ticket.item_name)
            if keyword_match:
                mapping = keyword_match
                dispatch_path = "item_mapping_by_keyword"
                match_detail = f"事项名称[{ticket.item_name}]关键词命中事项映射[{mapping.item_name}]"

        if mapping:
            dept_code = mapping.primary_dept_code
            dept_name = mapping.primary_dept_name
            dept_type = mapping.primary_dept_type
        elif ticket.item_name:
            dept_match = self._match_dept_by_item_name(ticket.item_name)
            if dept_match:
                dept_code, dept_name, dept_type = dept_match
                dispatch_path = "dept_name_match"
                match_detail = f"事项名称[{ticket.item_name}]命中部门[{dept_name}]"

        if not dept_code and ticket.problem_type:
            dept_code, dept_name, dept_type = self._get_dept_by_problem_type(
                ticket.problem_type, ticket.dept_code
            )
            if dispatch_path == "default_supervision":
                dispatch_path = "problem_type"
                match_detail = f"按问题类型[{ProblemType.get_description(ticket.problem_type)}]兜底分派"

        if not dept_code and ticket.dept_code:
            dept = self.db.query(Department).filter(
                Department.dept_code == ticket.dept_code,
                Department.is_active == True
            ).first()
            if dept:
                dept_code = dept.dept_code
                dept_name = dept.dept_name
                dept_type = dept.dept_type
                if dispatch_path == "default_supervision":
                    dispatch_path = "dept_code_match"
                    match_detail = f"按评价部门编码[{ticket.dept_code}]分派"

        if not dept_code:
            dept_code = "SUP001"
            dept_name = "营商环境督查室"
            dept_type = DepartmentType.SUPERVISION
            if dispatch_path == "default_supervision":
                match_detail = "无任何匹配项，兜底至营商环境督查室"

        timeout_hours = self._get_timeout_by_urgency(ticket.urgency_level)
        deadline = datetime.now() + timedelta(hours=timeout_hours)

        problem_desc = ProblemType.get_description(ticket.problem_type) if ticket.problem_type else "未分类"
        assignment = Assignment(
            ticket_id=ticket.id,
            from_dept_code="SUP001",
            from_dept_name="营商环境督查室",
            from_user="system",
            to_dept_code=dept_code,
            to_dept_name=dept_name,
            to_dept_type=dept_type,
            assign_reason=f"自动分派（{dispatch_path}）：{problem_desc}问题；{match_detail}",
            assign_time=datetime.now(),
            deadline=deadline,
            dispatch_path=dispatch_path
        )

        return assignment

    def _match_item_mapping_by_keywords(self, item_name: str) -> Optional[ItemMapping]:
        if not item_name:
            return None

        name_clean = item_name.strip()
        mappings = self.db.query(ItemMapping).filter(
            ItemMapping.is_active == True
        ).all()

        exact = [m for m in mappings if m.item_name and m.item_name == name_clean]
        if exact:
            return exact[0]

        contains = [m for m in mappings if m.item_name and (m.item_name in name_clean or name_clean in m.item_name)]
        if contains:
            return contains[0]

        for m in mappings:
            keywords = m.keywords or []
            for kw in keywords:
                if kw and kw in name_clean:
                    return m

        return None

    def _match_dept_by_item_name(self, item_name: str):
        if not item_name:
            return None

        name_clean = item_name.strip()
        depts = self.db.query(Department).filter(
            Department.is_active == True
        ).all()

        for dept in depts:
            if dept.dept_name and dept.dept_name in name_clean:
                return dept.dept_code, dept.dept_name, dept.dept_type

        keyword_to_dept = [
            (("不动产", "房产", "过户"), "不动产"),
            (("营业执照", "工商", "注册", "注销", "变更"), "市场"),
            (("纳税", "税务", "申报", "发票"), "税务"),
            (("身份证", "户籍"), "户籍"),
            (("系统", "网络", "登录"), "信息"),
        ]

        for keywords, hint in keyword_to_dept:
            if any(kw in name_clean for kw in keywords):
                for dept in depts:
                    if dept.dept_name and hint in dept.dept_name:
                        return dept.dept_code, dept.dept_name, dept.dept_type

        return None

    def manual_dispatch(self, data: TicketAssign, operator: str) -> Optional[Assignment]:
        ticket = self.db.query(Ticket).filter(Ticket.id == data.ticket_id).first()
        if not ticket:
            return None

        timeout_hours = self._get_timeout_by_urgency(ticket.urgency_level)
        deadline = data.deadline or (datetime.now() + timedelta(hours=timeout_hours))

        assignment = Assignment(
            ticket_id=data.ticket_id,
            from_dept_code="SUP001",
            from_dept_name="营商环境督查室",
            from_user=operator,
            to_dept_code=data.dept_code,
            to_dept_name=data.dept_name,
            to_dept_type=data.dept_type,
            to_user=data.assign_user,
            assign_reason=data.assign_reason or "人工分派",
            assign_time=datetime.now(),
            deadline=deadline
        )

        self.db.add(assignment)

        ticket.assigned_dept_code = data.dept_code
        ticket.assigned_dept_name = data.dept_name
        ticket.assigned_dept_type = data.dept_type
        ticket.assigned_user = data.assign_user
        ticket.status = TicketStatus.ASSIGNED
        ticket.deadline_time = deadline
        ticket.first_reminder_time = None
        ticket.last_reminder_time = None
        ticket.reminder_count = 0

        self.db.flush()

        self.trail_service.log_ticket_operation(
            ticket_id=ticket.id,
            operation_type="manual_dispatched",
            operation_desc=f"人工分派至{data.dept_name}",
            operator=operator,
            detail={
                "dept_code": data.dept_code,
                "dept_name": data.dept_name,
                "assign_user": data.assign_user,
                "assign_reason": data.assign_reason,
                "deadline": deadline.isoformat() if deadline else None
            }
        )

        self.db.commit()

        return assignment

    def accept_ticket(self, ticket_id: int, accept_user: str) -> bool:
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket or ticket.status != TicketStatus.ASSIGNED:
            return False

        assignment = self.db.query(Assignment).filter(
            Assignment.ticket_id == ticket_id,
            Assignment.is_accepted == False
        ).order_by(Assignment.assign_time.desc()).first()

        if assignment:
            assignment.is_accepted = True
            assignment.accept_time = datetime.now()
            assignment.accept_user = accept_user

        ticket.status = TicketStatus.ACCEPTED
        ticket.accept_time = datetime.now()

        self.trail_service.log_ticket_operation(
            ticket_id=ticket_id,
            operation_type="ticket_accepted",
            operation_desc=f"工单已接单",
            operator=accept_user,
            detail={
                "accept_user": accept_user,
                "accept_time": datetime.now().isoformat()
            }
        )

        self.db.commit()
        return True

    def reject_ticket(self, ticket_id: int, reject_reason: str, reject_user: str) -> bool:
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket or ticket.status != TicketStatus.ASSIGNED:
            return False

        assignment = self.db.query(Assignment).filter(
            Assignment.ticket_id == ticket_id,
            Assignment.is_accepted == False
        ).order_by(Assignment.assign_time.desc()).first()

        if assignment:
            assignment.is_rejected = True
            assignment.reject_reason = reject_reason
            assignment.reject_time = datetime.now()

        ticket.status = TicketStatus.PENDING
        ticket.assigned_dept_code = None
        ticket.assigned_dept_name = None
        ticket.assigned_dept_type = None
        ticket.assigned_user = None

        self.trail_service.log_ticket_operation(
            ticket_id=ticket_id,
            operation_type="ticket_rejected",
            operation_desc=f"工单被拒收",
            operator=reject_user,
            detail={
                "reject_user": reject_user,
                "reject_reason": reject_reason,
                "reject_time": datetime.now().isoformat()
            }
        )

        self.db.commit()
        return True

    def transfer_ticket(self, ticket_id: int, new_dept_code: str, new_dept_name: str,
                        new_dept_type: str, reason: str, operator: str) -> bool:
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return False

        timeout_hours = self._get_timeout_by_urgency(ticket.urgency_level)
        deadline = datetime.now() + timedelta(hours=timeout_hours)

        assignment = Assignment(
            ticket_id=ticket_id,
            from_dept_code=ticket.assigned_dept_code,
            from_dept_name=ticket.assigned_dept_name,
            from_user=operator,
            to_dept_code=new_dept_code,
            to_dept_name=new_dept_name,
            to_dept_type=new_dept_type,
            assign_reason=f"转派：{reason}",
            assign_time=datetime.now(),
            deadline=deadline
        )

        self.db.add(assignment)

        ticket.assigned_dept_code = new_dept_code
        ticket.assigned_dept_name = new_dept_name
        ticket.assigned_dept_type = new_dept_type
        ticket.status = TicketStatus.ASSIGNED
        ticket.deadline_time = deadline
        ticket.accept_time = None
        ticket.first_reminder_time = None
        ticket.last_reminder_time = None
        ticket.reminder_count = 0

        self.db.flush()

        self.trail_service.log_ticket_operation(
            ticket_id=ticket_id,
            operation_type="ticket_transferred",
            operation_desc=f"工单转派至{new_dept_name}",
            operator=operator,
            detail={
                "from_dept_code": ticket.assigned_dept_code,
                "to_dept_code": new_dept_code,
                "to_dept_name": new_dept_name,
                "transfer_reason": reason,
                "deadline": deadline.isoformat() if deadline else None
            }
        )

        self.db.commit()
        return True

    def _get_dept_by_problem_type(self, problem_type: str, default_dept_code: str = None):
        dept_map = {
            ProblemType.SERVICE_ATTITUDE: (DepartmentType.WINDOW, "窗口单位"),
            ProblemType.MATERIAL_INFORMATION: (DepartmentType.WINDOW, "窗口单位"),
            ProblemType.PROCESS_DURATION: (DepartmentType.APPROVAL, "审批科室"),
            ProblemType.SYSTEM_FAILURE: (DepartmentType.SUPPORT, "后台支撑部门"),
            ProblemType.DEPARTMENT_COORDINATION: (DepartmentType.SUPERVISION, "督查部门"),
            ProblemType.OTHER: (DepartmentType.SUPERVISION, "督查部门")
        }

        dept_type, default_name = dept_map.get(problem_type, (DepartmentType.SUPERVISION, "督查部门"))

        if default_dept_code:
            dept = self.db.query(Department).filter(
                Department.dept_code == default_dept_code,
                Department.is_active == True
            ).first()
            if dept:
                return dept.dept_code, dept.dept_name, dept.dept_type

        dept = self.db.query(Department).filter(
            Department.dept_type == dept_type,
            Department.is_active == True
        ).first()

        if dept:
            return dept.dept_code, dept.dept_name, dept.dept_type

        return "SUP001", default_name, DepartmentType.SUPERVISION

    def _get_timeout_by_urgency(self, urgency_level: str) -> int:
        timeout_map = {
            UrgencyLevel.NORMAL: settings.FEEDBACK_TIMEOUT_HOURS,
            UrgencyLevel.URGENT: 24,
            UrgencyLevel.MAJOR: 12,
            UrgencyLevel.SENSITIVE: 6
        }
        return timeout_map.get(urgency_level, settings.FEEDBACK_TIMEOUT_HOURS)
