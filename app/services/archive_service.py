from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
import json

from app.core.models import Ticket, Archive, Evaluation, Assignment, Reminder, OperationLog
from app.core.enums import TicketStatus
from app.services.trail_service import TrailService


class ArchiveService:
    def __init__(self, db: Session):
        self.db = db
        self.trail_service = TrailService(db)

    def generate_closing_statement(self, ticket: Ticket) -> str:
        from app.core.enums import ProblemType, EvaluationLevel, DataSource

        source_descs = []
        for eval_item in ticket.evaluations:
            source_descs.append(DataSource.get_description(eval_item.source))

        sources_text = "、".join(set(source_descs)) if source_descs else "多渠道"

        problem_desc = ProblemType.get_description(ticket.problem_type)

        statement_parts = [
            f"尊敬的办事群众：",
            f"",
            f"您通过{sources_text}反映的关于【{ticket.item_name or '相关事项'}】的{problem_desc}问题，我们已处理完毕。",
            f"",
            f"处理情况说明：",
            f"{ticket.handle_result or '已按照相关规定进行了调查处理'}",
            f"",
            f"整改措施：",
            f"{ticket.handle_measure or '已采取相应措施进行整改'}",
            f"",
            f"感谢您的监督与反馈，我们将持续改进服务质量。",
            f"",
            f"营商环境督查室",
            f"{datetime.now().strftime('%Y年%m月%d日')}"
        ]

        return "\n".join(statement_parts)

    def _get_source_desc(self, source: str) -> str:
        from app.core.enums import DataSource
        return DataSource.get_description(source)

    def complete_ticket(self, ticket_id: int, conclusion: str,
                     closing_statement: Optional[str] = None,
                     citizen_satisfaction: Optional[str] = None,
                     is_satisfied: bool = False,
                     operator: str = "system") -> Optional[Archive]:
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket or ticket.status in [TicketStatus.COMPLETED, TicketStatus.CLOSED]:
            return None

        if not closing_statement:
            closing_statement = self.generate_closing_statement(ticket)

        ticket.status = TicketStatus.COMPLETED
        ticket.conclusion = conclusion
        ticket.closing_statement = closing_statement
        ticket.citizen_satisfaction = citizen_satisfaction
        ticket.is_satisfied = is_satisfied
        ticket.completed_time = datetime.now()

        archive = self.create_archive(ticket, operator)

        self.trail_service.log_ticket_operation(
            ticket_id=ticket.id,
            operation_type="ticket_completed",
            operation_desc="工单办结归档",
            operator=operator,
            detail={
                "conclusion": conclusion,
                "is_satisfied": is_satisfied,
                "satisfaction": citizen_satisfaction
            }
        )

        self.db.commit()
        self.db.refresh(archive)

        return archive

    def create_archive(self, ticket: Ticket, operator: str = "system") -> Archive:
        archive_no = self._generate_archive_no()

        ticket_snapshot = self._ticket_to_dict(ticket)
        evaluations_snapshot = [self._evaluation_to_dict(e) for e in ticket.evaluations]
        assignments_snapshot = [self._assignment_to_dict(a) for a in ticket.assignments]
        reminders_snapshot = [self._reminder_to_dict(r) for r in ticket.reminders]
        operation_logs_snapshot = [self._oplog_to_dict(o) for o in ticket.operation_logs]

        archive = Archive(
            ticket_id=ticket.id,
            archive_no=archive_no,
            archive_type="normal",
            archive_time=datetime.now(),
            ticket_snapshot=ticket_snapshot,
            evaluations_snapshot=evaluations_snapshot,
            operation_logs_snapshot=operation_logs_snapshot,
            reminders_snapshot=reminders_snapshot,
            assignments_snapshot=assignments_snapshot,
            closing_statement=ticket.closing_statement,
            final_conclusion=ticket.conclusion,
            citizen_satisfaction=ticket.citizen_satisfaction,
            archivist=operator,
            archive_remark="自动归档",
            retention_period=3650,
            is_permanent=ticket.urgency_level in ["major", "sensitive"]
        )

        self.db.add(archive)
        self.db.flush()

        return archive

    def _ticket_to_dict(self, ticket: Ticket) -> Dict[str, Any]:
        return {
            "id": ticket.id,
            "ticket_no": ticket.ticket_no,
            "status": ticket.status,
            "problem_type": ticket.problem_type,
            "urgency_level": ticket.urgency_level,
            "citizen_name": ticket.citizen_name,
            "citizen_phone": ticket.citizen_phone,
            "item_code": ticket.item_code,
            "item_name": ticket.item_name,
            "summary": ticket.summary,
            "content": ticket.content,
            "assigned_dept_code": ticket.assigned_dept_code,
            "assigned_dept_name": ticket.assigned_dept_name,
            "assigned_dept_type": ticket.assigned_dept_type,
            "deadline_time": ticket.deadline_time.isoformat() if ticket.deadline_time else None,
            "handler": ticket.handler,
            "handle_result": ticket.handle_result,
            "handle_measure": ticket.handle_measure,
            "feedback_time": ticket.feedback_time.isoformat() if ticket.feedback_time else None,
            "reviewer": ticket.reviewer,
            "review_opinion": ticket.review_opinion,
            "review_time": ticket.review_time.isoformat() if ticket.review_time else None,
            "conclusion": ticket.conclusion,
            "closing_statement": ticket.closing_statement,
            "completed_time": ticket.completed_time.isoformat() if ticket.completed_time else None,
            "is_escalated": ticket.is_escalated,
            "escalated_time": ticket.escalated_time.isoformat() if ticket.escalated_time else None,
            "escalated_to": ticket.escalated_to,
            "escalation_reason": ticket.escalation_reason,
            "citizen_satisfaction": ticket.citizen_satisfaction,
            "is_satisfied": ticket.is_satisfied,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        }

    def _evaluation_to_dict(self, evaluation: Evaluation) -> Dict[str, Any]:
        return {
            "id": evaluation.id,
            "evaluation_no": evaluation.evaluation_no,
            "source": evaluation.source,
            "level": evaluation.level,
            "score": evaluation.score,
            "content": evaluation.content,
            "suggestion": evaluation.suggestion,
            "item_code": evaluation.item_code,
            "item_name": evaluation.item_name,
            "dept_code": evaluation.dept_code,
            "dept_name": evaluation.dept_name,
            "problem_type": evaluation.problem_type,
            "urgency_level": evaluation.urgency_level,
            "is_duplicate": evaluation.is_duplicate,
            "evaluate_time": evaluation.evaluate_time.isoformat() if evaluation.evaluate_time else None,
            "happen_time": evaluation.happen_time.isoformat() if evaluation.happen_time else None,
        }

    def _assignment_to_dict(self, assignment: Assignment) -> Dict[str, Any]:
        return {
            "id": assignment.id,
            "from_dept_code": assignment.from_dept_code,
            "from_dept_name": assignment.from_dept_name,
            "to_dept_code": assignment.to_dept_code,
            "to_dept_name": assignment.to_dept_name,
            "to_dept_type": assignment.to_dept_type,
            "assign_reason": assignment.assign_reason,
            "assign_time": assignment.assign_time.isoformat() if assignment.assign_time else None,
            "deadline": assignment.deadline.isoformat() if assignment.deadline else None,
            "is_accepted": assignment.is_accepted,
            "accept_time": assignment.accept_time.isoformat() if assignment.accept_time else None,
            "is_rejected": assignment.is_rejected,
            "reject_reason": assignment.reject_reason,
        }

    def _reminder_to_dict(self, reminder: Reminder) -> Dict[str, Any]:
        return {
            "id": reminder.id,
            "reminder_type": reminder.reminder_type,
            "reminder_level": reminder.reminder_level,
            "reminder_time": reminder.reminder_time.isoformat() if reminder.reminder_time else None,
            "reminded_dept_name": reminder.reminded_dept_name,
            "content": reminder.content,
            "is_escalation": reminder.is_escalation,
            "escalated_to": reminder.escalated_to,
            "sent_by_system": reminder.sent_by_system,
            "operator": reminder.operator,
        }

    def _oplog_to_dict(self, oplog: OperationLog) -> Dict[str, Any]:
        return {
            "id": oplog.id,
            "operation_type": oplog.operation_type,
            "operation_desc": oplog.operation_desc,
            "operation_detail": oplog.operation_detail,
            "operator": oplog.operator,
            "operator_dept": oplog.operator_dept,
            "operation_time": oplog.operation_time.isoformat() if oplog.operation_time else None,
        }

    def _generate_archive_no(self) -> str:
        date_str = datetime.now().strftime("%Y%m")
        random_str = str(uuid.uuid4().hex[:6]).upper()
        return f"AR{date_str}{random_str}"

    def get_archive(self, archive_id: int) -> Optional[Archive]:
        return self.db.query(Archive).filter(Archive.id == archive_id).first()

    def get_archive_by_no(self, archive_no: str) -> Optional[Archive]:
        return self.db.query(Archive).filter(Archive.archive_no == archive_no).first()

    def get_archive_by_ticket(self, ticket_id: int) -> Optional[Archive]:
        return self.db.query(Archive).filter(Archive.ticket_id == ticket_id).first()

    def query_archives(self, start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         dept_code: Optional[str] = None,
                         problem_type: Optional[str] = None,
                         is_satisfied: Optional[bool] = None,
                         page: int = 1,
                         page_size: int = 20):
        q = self.db.query(Archive)

        if start_time:
            q = q.filter(Archive.archive_time >= start_time)
        if end_time:
            q = q.filter(Archive.archive_time <= end_time)

        if dept_code or problem_type or is_satisfied is not None:
            q = q.join(Ticket)
            if dept_code:
                q = q.filter(Ticket.assigned_dept_code == dept_code)
            if problem_type:
                q = q.filter(Ticket.problem_type == problem_type)
            if is_satisfied is not None:
                q = q.filter(Ticket.is_satisfied == is_satisfied)

        total = q.count()
        items = q.order_by(Archive.archive_time.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return items, total

    def auto_archive_completed(self, days: int = 30) -> List[Archive]:
        cutoff_time = datetime.now() - timedelta(days=days)

        tickets = self.db.query(Ticket).filter(
            Ticket.status == TicketStatus.COMPLETED,
            Ticket.completed_time <= cutoff_time
        ).all()

        archives = []
        for ticket in tickets:
            existing = self.get_archive_by_ticket(ticket.id)
            if not existing:
                archive = self.create_archive(ticket, "system")
                archives.append(archive)

        self.db.commit()
        return archives
