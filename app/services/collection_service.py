from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import uuid

from app.core.models import Evaluation, Ticket, OperationLog
from app.core.enums import (
    DataSource, EvaluationLevel, TicketStatus,
    UrgencyLevel, ProblemType
)
from app.schemas.evaluation import EvaluationCreate, EvaluationBatchCreate
from app.schemas.ticket import TicketCreate
from app.services.judgment_service import JudgmentService
from app.services.dispatch_service import DispatchService
from app.services.trail_service import TrailService


class CollectionService:
    def __init__(self, db: Session):
        self.db = db
        self.judgment_service = JudgmentService(db)
        self.dispatch_service = DispatchService(db)
        self.trail_service = TrailService(db)

    def receive_evaluation(self, data: EvaluationCreate, operator: str = "system") -> Evaluation:
        existing = self.db.query(Evaluation).filter(
            Evaluation.evaluation_no == data.evaluation_no
        ).first()
        if existing:
            return existing

        evaluation = Evaluation(
            evaluation_no=data.evaluation_no,
            source=data.source,
            level=data.level,
            score=data.score,
            citizen_id=data.citizen_id,
            citizen_name=data.citizen_name,
            citizen_phone=data.citizen_phone,
            citizen_id_card=data.citizen_id_card,
            item_code=data.item_code,
            item_name=data.item_name,
            item_category=data.item_category,
            dept_code=data.dept_code,
            dept_name=data.dept_name,
            window_no=data.window_no,
            handler_name=data.handler_name,
            content=data.content,
            suggestion=data.suggestion,
            happen_time=data.happen_time,
            evaluate_time=data.evaluate_time or datetime.now()
        )

        problem_type = self.judgment_service.classify_problem_type(evaluation.content or "")
        evaluation.problem_type = problem_type

        is_duplicate, original_id = self.judgment_service.detect_duplicate(evaluation)
        evaluation.is_duplicate = is_duplicate
        evaluation.duplicate_of = original_id

        evaluation.urgency_level = self.judgment_service.judge_urgency(evaluation)

        self.db.add(evaluation)
        self.db.flush()

        self.trail_service.log_evaluation_operation(
            evaluation_id=evaluation.id,
            operation_type="evaluation_received",
            operation_desc=f"收到{DataSource.get_description(evaluation.source)}评价数据",
            operator=operator
        )

        if EvaluationLevel.is_negative(evaluation.level) and not evaluation.is_duplicate:
            self._create_ticket_for_evaluation(evaluation, operator)
        elif evaluation.is_duplicate and original_id:
            original_eval = self.db.query(Evaluation).filter(Evaluation.id == original_id).first()
            if original_eval and original_eval.ticket_id:
                evaluation.ticket_id = original_eval.ticket_id
                self.trail_service.log_ticket_operation(
                    ticket_id=original_eval.ticket_id,
                    operation_type="duplicate_merged",
                    operation_desc=f"合并重复评价[{evaluation.evaluation_no}]",
                    operator=operator,
                    detail={"duplicate_evaluation_id": evaluation.id}
                )

        self.db.commit()
        self.db.refresh(evaluation)
        return evaluation

    def receive_batch_evaluations(self, data: EvaluationBatchCreate, operator: str = "system") -> List[Evaluation]:
        results = []
        for eval_data in data.evaluations:
            eval_data.source = data.source
            result = self.receive_evaluation(eval_data, operator)
            results.append(result)
        return results

    def _create_ticket_for_evaluation(self, evaluation: Evaluation, operator: str):
        ticket_no = self._generate_ticket_no()

        ticket_data = TicketCreate(
            ticket_no=ticket_no,
            problem_type=evaluation.problem_type or ProblemType.OTHER,
            urgency_level=evaluation.urgency_level or UrgencyLevel.NORMAL,
            citizen_id=evaluation.citizen_id,
            citizen_name=evaluation.citizen_name,
            citizen_phone=evaluation.citizen_phone,
            citizen_id_card=evaluation.citizen_id_card,
            item_code=evaluation.item_code,
            item_name=evaluation.item_name,
            item_category=evaluation.item_category,
            summary=f"{EvaluationLevel.get_description(evaluation.level)}：{evaluation.item_name or '未知事项'}",
            content=evaluation.content,
            evaluation_ids=[evaluation.id]
        )

        ticket = Ticket(
            ticket_no=ticket_data.ticket_no,
            status=TicketStatus.PENDING,
            problem_type=ticket_data.problem_type,
            urgency_level=ticket_data.urgency_level,
            citizen_id=ticket_data.citizen_id,
            citizen_name=ticket_data.citizen_name,
            citizen_phone=ticket_data.citizen_phone,
            citizen_id_card=ticket_data.citizen_id_card,
            item_code=ticket_data.item_code,
            item_name=ticket_data.item_name,
            item_category=ticket_data.item_category,
            summary=ticket_data.summary,
            content=ticket_data.content
        )

        self.db.add(ticket)
        self.db.flush()

        evaluation.ticket_id = ticket.id

        self.trail_service.log_ticket_operation(
            ticket_id=ticket.id,
            operation_type="ticket_created",
            operation_desc=f"创建督办工单，来源评价[{evaluation.evaluation_no}]",
            operator=operator,
            detail={"evaluation_id": evaluation.id}
        )

        dispatch_result = self.dispatch_service.auto_dispatch(ticket)
        if dispatch_result:
            self.db.add(dispatch_result)
            ticket.assigned_dept_code = dispatch_result.to_dept_code
            ticket.assigned_dept_name = dispatch_result.to_dept_name
            ticket.assigned_dept_type = dispatch_result.to_dept_type
            ticket.assigned_user = dispatch_result.to_user
            ticket.status = TicketStatus.ASSIGNED
            ticket.deadline_time = dispatch_result.deadline

            self.trail_service.log_ticket_operation(
                ticket_id=ticket.id,
                operation_type="auto_dispatched",
                operation_desc=f"自动分派至{dispatch_result.to_dept_name}",
                operator=operator,
                detail={"dept_code": dispatch_result.to_dept_code, "deadline": dispatch_result.deadline.isoformat() if dispatch_result.deadline else None}
            )

        if self.judgment_service.is_major_sensitive(evaluation):
            ticket.is_escalated = True
            ticket.escalated_time = datetime.now()
            ticket.escalated_to = "营商环境督查室"
            ticket.escalation_reason = "重大敏感差评自动升级"
            ticket.status = TicketStatus.ESCALATED

            self.trail_service.log_ticket_operation(
                ticket_id=ticket.id,
                operation_type="auto_escalated",
                operation_desc="重大敏感差评自动升级报送",
                operator=operator,
                detail={"reason": "重大敏感差评"}
            )

        return ticket

    def _generate_ticket_no(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = str(uuid.uuid4().hex[:8]).upper()
        return f"DC{date_str}{random_str}"

    def get_evaluation(self, evaluation_id: int) -> Optional[Evaluation]:
        return self.db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()

    def get_evaluation_by_no(self, evaluation_no: str) -> Optional[Evaluation]:
        return self.db.query(Evaluation).filter(Evaluation.evaluation_no == evaluation_no).first()

    def query_evaluations(self, query_params):
        q = self.db.query(Evaluation)

        if query_params.source:
            q = q.filter(Evaluation.source == query_params.source)
        if query_params.level:
            q = q.filter(Evaluation.level == query_params.level)
        if query_params.problem_type:
            q = q.filter(Evaluation.problem_type == query_params.problem_type)
        if query_params.urgency_level:
            q = q.filter(Evaluation.urgency_level == query_params.urgency_level)
        if query_params.is_duplicate is not None:
            q = q.filter(Evaluation.is_duplicate == query_params.is_duplicate)
        if query_params.has_ticket is not None:
            if query_params.has_ticket:
                q = q.filter(Evaluation.ticket_id.isnot(None))
            else:
                q = q.filter(Evaluation.ticket_id.is_(None))
        if query_params.citizen_phone:
            q = q.filter(Evaluation.citizen_phone == query_params.citizen_phone)
        if query_params.item_code:
            q = q.filter(Evaluation.item_code == query_params.item_code)
        if query_params.dept_code:
            q = q.filter(Evaluation.dept_code == query_params.dept_code)
        if query_params.start_time:
            q = q.filter(Evaluation.evaluate_time >= query_params.start_time)
        if query_params.end_time:
            q = q.filter(Evaluation.evaluate_time <= query_params.end_time)

        total = q.count()
        items = q.order_by(Evaluation.evaluate_time.desc()) \
            .offset((query_params.page - 1) * query_params.page_size) \
            .limit(query_params.page_size) \
            .all()

        return items, total

    def get_duplicate_evaluations(self, evaluation_id: int) -> List[Evaluation]:
        return self.db.query(Evaluation).filter(
            Evaluation.duplicate_of == evaluation_id
        ).all()
