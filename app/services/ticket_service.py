from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any

from app.core.models import Ticket, Evaluation, Assignment, OperationLog
from app.core.enums import TicketStatus, DataSource
from app.schemas.ticket import (
    TicketProcess, TicketFeedback, TicketReview, TicketComplete, TicketQuery
)
from app.services.trail_service import TrailService
from app.services.archive_service import ArchiveService
from app.services.dispatch_service import DispatchService


class TicketService:
    def __init__(self, db: Session):
        self.db = db
        self.trail_service = TrailService(db)
        self.archive_service = ArchiveService(db)

    def get_ticket(self, ticket_id: int) -> Optional[Ticket]:
        return self.db.query(Ticket).filter(Ticket.id == ticket_id).first()

    def get_ticket_by_no(self, ticket_no: str) -> Optional[Ticket]:
        return self.db.query(Ticket).filter(Ticket.ticket_no == ticket_no).first()

    def get_ticket_with_detail(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return None

        result = {c.name: getattr(ticket, c.name) for c in ticket.__table__.columns}
        result["status"] = ticket.status
        result["problem_type"] = ticket.problem_type
        result["urgency_level"] = ticket.urgency_level
        result["assigned_dept_type"] = ticket.assigned_dept_type

        assignments = self.db.query(Assignment).filter(
            Assignment.ticket_id == ticket.id
        ).order_by(Assignment.assign_time.asc()).all()

        assignment_history = []
        latest_assignment = None
        for a in assignments:
            item = {
                "id": a.id,
                "from_dept_code": a.from_dept_code,
                "from_dept_name": a.from_dept_name,
                "to_dept_code": a.to_dept_code,
                "to_dept_name": a.to_dept_name,
                "to_dept_type": a.to_dept_type,
                "to_user": a.to_user,
                "assign_reason": a.assign_reason,
                "assign_time": a.assign_time,
                "deadline": a.deadline,
                "dispatch_path": a.dispatch_path,
                "dispatch_path_desc": DispatchService.get_dispatch_path_desc(a.dispatch_path),
                "is_accepted": a.is_accepted,
                "accept_time": a.accept_time,
                "is_rejected": a.is_rejected,
                "reject_reason": a.reject_reason,
                "reject_time": a.reject_time,
            }
            assignment_history.append(item)
            latest_assignment = item

        result["assignment_history"] = assignment_history
        result["latest_assignment"] = latest_assignment

        if latest_assignment and latest_assignment.get("dispatch_path"):
            result["dispatch_path"] = latest_assignment.get("dispatch_path")
            result["dispatch_path_desc"] = latest_assignment.get("dispatch_path_desc")
        else:
            auto_log = self.db.query(OperationLog).filter(
                OperationLog.ticket_id == ticket.id,
                OperationLog.operation_type == "auto_dispatched"
            ).order_by(OperationLog.operation_time.desc()).first()
            dispatch_path = None
            if auto_log and auto_log.operation_detail:
                dispatch_path = auto_log.operation_detail.get("dispatch_path")
            result["dispatch_path"] = dispatch_path
            result["dispatch_path_desc"] = DispatchService.get_dispatch_path_desc(dispatch_path)

        evaluations = self.db.query(Evaluation).filter(
            Evaluation.ticket_id == ticket.id
        ).order_by(Evaluation.evaluate_time.asc()).all()

        duplicate_target_ids = set(e.duplicate_of for e in evaluations if e.is_duplicate and e.duplicate_of)
        eval_infos = []
        for e in evaluations:
            is_original = (not e.is_duplicate) or (e.id in duplicate_target_ids)
            if is_original and not e.is_duplicate:
                role = "original"
            elif e.is_duplicate:
                role = "merged"
            else:
                role = "original"
            eval_infos.append({
                "id": e.id,
                "evaluation_no": e.evaluation_no,
                "source": e.source,
                "source_desc": DataSource.get_description(e.source),
                "level": e.level,
                "content": e.content,
                "evaluate_time": e.evaluate_time,
                "is_duplicate": e.is_duplicate,
                "is_original": is_original,
                "role": role,
                "citizen_name": e.citizen_name,
                "citizen_phone": e.citizen_phone
            })

        result["related_evaluations"] = eval_infos

        original_list = [e for e in eval_infos if e["is_original"]]
        merged_list = [e for e in eval_infos if e["is_duplicate"]]
        source_channels = sorted(set(e["source_desc"] for e in eval_infos))
        all_times = [e["evaluate_time"] for e in eval_infos]

        result["merged_summary"] = {
            "original_evaluation": original_list[0] if original_list else None,
            "merged_evaluations": merged_list,
            "total_count": len(eval_infos),
            "source_channels": source_channels,
            "first_time": min(all_times) if all_times else None,
            "last_time": max(all_times) if all_times else None,
            "timeline": eval_infos
        }

        operation_logs = self.db.query(OperationLog).filter(
            OperationLog.ticket_id == ticket.id
        ).order_by(OperationLog.operation_time.asc()).all()

        result["operation_trail"] = [
            {
                "id": log.id,
                "operation_type": log.operation_type,
                "operation_desc": log.operation_desc,
                "operation_detail": log.operation_detail,
                "operator": log.operator,
                "operator_dept": log.operator_dept,
                "operation_time": log.operation_time
            }
            for log in operation_logs
        ]

        return result

    def get_ticket_by_no_with_detail(self, ticket_no: str) -> Optional[Dict[str, Any]]:
        ticket = self.get_ticket_by_no(ticket_no)
        if not ticket:
            return None
        return self.get_ticket_with_detail(ticket.id)

    def process_ticket(self, data: TicketProcess, operator: str) -> bool:
        ticket = self.get_ticket(data.ticket_id)
        if not ticket or ticket.status not in [TicketStatus.ACCEPTED, TicketStatus.PROCESSING]:
            return False

        ticket.status = TicketStatus.PROCESSING
        ticket.handler = data.handler
        if data.handle_result:
            ticket.handle_result = data.handle_result
        if data.handle_measure:
            ticket.handle_measure = data.handle_measure

        self.trail_service.log_ticket_operation(
            ticket_id=ticket.id,
            operation_type="ticket_processing",
            operation_desc="更新处理进度",
            operator=operator,
            detail={
                "handler": data.handler,
                "handle_result": data.handle_result,
                "handle_measure": data.handle_measure
            }
        )

        self.db.commit()
        return True

    def submit_feedback(self, data: TicketFeedback, operator: str) -> bool:
        ticket = self.get_ticket(data.ticket_id)
        if not ticket or ticket.status not in [TicketStatus.ACCEPTED, TicketStatus.PROCESSING]:
            return False

        ticket.status = TicketStatus.FEEDBACK
        ticket.handle_result = data.handle_result
        ticket.handle_measure = data.handle_measure
        ticket.handler = data.handler
        ticket.feedback_time = data.feedback_time or datetime.now()

        self.trail_service.log_ticket_operation(
            ticket_id=ticket.id,
            operation_type="feedback_submitted",
            operation_desc="提交处理结果待审核",
            operator=operator,
            detail={
                "handler": data.handler,
                "handle_result": data.handle_result,
                "handle_measure": data.handle_measure
            }
        )

        self.db.commit()
        return True

    def review_ticket(self, data: TicketReview, operator: str) -> bool:
        ticket = self.get_ticket(data.ticket_id)
        if not ticket or ticket.status != TicketStatus.FEEDBACK:
            return False

        ticket.reviewer = data.reviewer
        ticket.review_opinion = data.review_opinion
        ticket.review_time = datetime.now()

        if data.is_passed:
            self.trail_service.log_ticket_operation(
                ticket_id=ticket.id,
                operation_type="review_passed",
                operation_desc="复核通过，准备办结",
                operator=operator,
                detail={
                    "reviewer": data.reviewer,
                    "review_opinion": data.review_opinion
                }
            )
        else:
            ticket.status = TicketStatus.PROCESSING

            self.trail_service.log_ticket_operation(
                ticket_id=ticket.id,
                operation_type="review_rejected",
                operation_desc="复核不通过，退回重新处理",
                operator=operator,
                detail={
                    "reviewer": data.reviewer,
                    "review_opinion": data.review_opinion
                }
            )

        if data.citizen_satisfaction:
            ticket.citizen_satisfaction = data.citizen_satisfaction

        self.db.commit()
        return True

    def complete_ticket(self, data: TicketComplete, operator: str) -> bool:
        ticket = self.get_ticket(data.ticket_id)
        if not ticket:
            return False

        archive = self.archive_service.complete_ticket(
            ticket_id=data.ticket_id,
            conclusion=data.conclusion,
            closing_statement=data.closing_statement,
            citizen_satisfaction=data.citizen_satisfaction,
            is_satisfied=data.is_satisfied,
            operator=operator
        )

        return archive is not None

    def query_tickets(self, query_params: TicketQuery) -> Tuple[List[Ticket], int]:
        q = self.db.query(Ticket)

        if query_params.status:
            q = q.filter(Ticket.status == query_params.status)
        if query_params.problem_type:
            q = q.filter(Ticket.problem_type == query_params.problem_type)
        if query_params.urgency_level:
            q = q.filter(Ticket.urgency_level == query_params.urgency_level)
        if query_params.assigned_dept_code:
            q = q.filter(Ticket.assigned_dept_code == query_params.assigned_dept_code)
        if query_params.citizen_phone:
            q = q.filter(Ticket.citizen_phone == query_params.citizen_phone)
        if query_params.item_code:
            q = q.filter(Ticket.item_code == query_params.item_code)
        if query_params.is_escalated is not None:
            q = q.filter(Ticket.is_escalated == query_params.is_escalated)
        if query_params.is_overdue is not None:
            now = datetime.now()
            if query_params.is_overdue:
                q = q.filter(
                    Ticket.status.in_([
                        TicketStatus.ASSIGNED,
                        TicketStatus.ACCEPTED,
                        TicketStatus.PROCESSING
                    ]),
                    Ticket.deadline_time <= now
                )
            else:
                q = q.filter(
                    or_(
                        Ticket.status.in_([TicketStatus.COMPLETED, TicketStatus.CLOSED]),
                        Ticket.deadline_time > now
                    )
                )
        if query_params.start_time:
            q = q.filter(Ticket.created_at >= query_params.start_time)
        if query_params.end_time:
            q = q.filter(Ticket.created_at <= query_params.end_time)

        total = q.count()
        items = q.order_by(Ticket.created_at.desc()) \
            .offset((query_params.page - 1) * query_params.page_size) \
            .limit(query_params.page_size) \
            .all()

        return items, total

    def get_ticket_status(self, ticket_no: str) -> Optional[dict]:
        ticket = self.get_ticket_by_no(ticket_no)
        if not ticket:
            return None

        now = datetime.now()
        remaining_hours = None
        is_overdue = False

        if ticket.deadline_time and ticket.status not in [TicketStatus.COMPLETED, TicketStatus.CLOSED]:
            delta = ticket.deadline_time - now
            remaining_hours = delta.total_seconds() / 3600
            is_overdue = remaining_hours < 0

        current_step = self._get_current_step(ticket.status)

        return {
            "ticket_no": ticket.ticket_no,
            "status": ticket.status,
            "status_desc": TicketStatus.get_description(ticket.status),
            "current_step": current_step,
            "handler": ticket.handler,
            "deadline_time": ticket.deadline_time,
            "remaining_hours": remaining_hours,
            "is_overdue": is_overdue,
            "closing_statement": ticket.closing_statement,
            "citizen_satisfaction": ticket.citizen_satisfaction
        }

    def _get_current_step(self, status: str) -> str:
        step_map = {
            TicketStatus.PENDING: "第一步：待分派",
            TicketStatus.ASSIGNED: "第二步：待接单",
            TicketStatus.ACCEPTED: "第三步：处理中",
            TicketStatus.PROCESSING: "第三步：处理中",
            TicketStatus.FEEDBACK: "第四步：待复核",
            TicketStatus.REVIEWING: "第四步：复核中",
            TicketStatus.ESCALATED: "升级处理中",
            TicketStatus.COMPLETED: "第五步：已办结",
            TicketStatus.CLOSED: "已关闭"
        }
        return step_map.get(status, "未知状态")

    def get_ticket_evaluations(self, ticket_id: int) -> List[Evaluation]:
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return []
        return ticket.evaluations

    def reopen_ticket(self, ticket_id: int, reason: str, operator: str) -> bool:
        ticket = self.get_ticket(ticket_id)
        if not ticket or ticket.status not in [TicketStatus.COMPLETED, TicketStatus.CLOSED]:
            return False

        ticket.status = TicketStatus.PROCESSING
        ticket.completed_time = None
        ticket.closing_statement = None
        ticket.conclusion = None

        self.trail_service.log_ticket_operation(
            ticket_id=ticket_id,
            operation_type="ticket_reopened",
            operation_desc=f"工单重新打开：{reason}",
            operator=operator,
            detail={"reason": reason}
        )

        self.db.commit()
        return True

    def close_ticket(self, ticket_id: int, reason: str, operator: str) -> bool:
        ticket = self.get_ticket(ticket_id)
        if not ticket or ticket.status == TicketStatus.CLOSED:
            return False

        ticket.status = TicketStatus.CLOSED
        ticket.completed_time = datetime.now()

        self.trail_service.log_ticket_operation(
            ticket_id=ticket_id,
            operation_type="ticket_closed",
            operation_desc=f"工单关闭：{reason}",
            operator=operator,
            detail={"reason": reason}
        )

        self.db.commit()
        return True
