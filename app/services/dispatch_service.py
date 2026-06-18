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

        mapping = None
        if ticket.item_code:
            mapping = self.db.query(ItemMapping).filter(
                ItemMapping.item_code == ticket.item_code,
                ItemMapping.is_active == True
            ).first()

        if mapping:
            dept_code = mapping.primary_dept_code
            dept_name = mapping.primary_dept_name
            dept_type = mapping.primary_dept_type
        elif ticket.problem_type:
            dept_code, dept_name, dept_type = self._get_dept_by_problem_type(
                ticket.problem_type, ticket.dept_code
            )
        elif ticket.dept_code:
            dept = self.db.query(Department).filter(
                Department.dept_code == ticket.dept_code,
                Department.is_active == True
            ).first()
            if dept:
                dept_code = dept.dept_code
                dept_name = dept.dept_name
                dept_type = dept.dept_type

        if not dept_code:
            dept_code = "SUP001"
            dept_name = "营商环境督查室"
            dept_type = DepartmentType.SUPERVISION

        timeout_hours = self._get_timeout_by_urgency(ticket.urgency_level)
        deadline = datetime.now() + timedelta(hours=timeout_hours)

        assignment = Assignment(
            ticket_id=ticket.id,
            from_dept_code="SUP001",
            from_dept_name="营商环境督查室",
            from_user="system",
            to_dept_code=dept_code,
            to_dept_name=dept_name,
            to_dept_type=dept_type,
            assign_reason=f"自动分派：{ProblemType.get_description(ticket.problem_type)}问题",
            assign_time=datetime.now(),
            deadline=deadline
        )

        return assignment

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
