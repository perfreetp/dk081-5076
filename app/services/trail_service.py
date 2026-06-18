from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.models import OperationLog
from typing import Optional


class TrailService:
    def __init__(self, db: Session):
        self.db = db

    def log_ticket_operation(self, ticket_id: int, operation_type: str,
                                 operation_desc: str, operator: str = "system",
                                 operator_dept: Optional[str] = None,
                                 detail: Optional[Dict[str, Any]] = None,
                                 ip_address: Optional[str] = None,
                                 user_agent: Optional[str] = None) -> OperationLog:
        log = OperationLog(
            ticket_id=ticket_id,
            operation_type=operation_type,
            operation_desc=operation_desc,
            operation_detail=detail,
            operator=operator,
            operator_dept=operator_dept,
            operation_time=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.db.add(log)
        self.db.flush()
        return log

    def log_evaluation_operation(self, evaluation_id: int, operation_type: str,
                                     operation_desc: str, operator: str = "system",
                                     operator_dept: Optional[str] = None,
                                     detail: Optional[Dict[str, Any]] = None,
                                     ip_address: Optional[str] = None,
                                     user_agent: Optional[str] = None) -> OperationLog:
        log = OperationLog(
            evaluation_id=evaluation_id,
            operation_type=operation_type,
            operation_desc=operation_desc,
            operation_detail=detail,
            operator=operator,
            operator_dept=operator_dept,
            operation_time=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.db.add(log)
        self.db.flush()
        return log

    def get_ticket_trail(self, ticket_id: int) -> List[OperationLog]:
        return self.db.query(OperationLog).filter(
            OperationLog.ticket_id == ticket_id
        ).order_by(OperationLog.operation_time.asc()).all()

    def get_evaluation_trail(self, evaluation_id: int) -> List[OperationLog]:
        return self.db.query(OperationLog).filter(
            OperationLog.evaluation_id == evaluation_id
        ).order_by(OperationLog.operation_time.asc()).all()

    def get_operation_logs(self, ticket_id: Optional[int] = None,
                             evaluation_id: Optional[int] = None,
                             operator: Optional[str] = None,
                             operation_type: Optional[str] = None,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             page: int = 1,
                             page_size: int = 20):
        q = self.db.query(OperationLog)

        if ticket_id:
            q = q.filter(OperationLog.ticket_id == ticket_id)
        if evaluation_id:
            q = q.filter(OperationLog.evaluation_id == evaluation_id)
        if operator:
            q = q.filter(OperationLog.operator == operator)
        if operation_type:
            q = q.filter(OperationLog.operation_type == operation_type)
        if start_time:
            q = q.filter(OperationLog.operation_time >= start_time)
        if end_time:
            q = q.filter(OperationLog.operation_time <= end_time)

        total = q.count()
        items = q.order_by(OperationLog.operation_time.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return items, total
