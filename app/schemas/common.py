from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional, List, Dict, Any
from datetime import datetime

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(200, description="响应码")
    message: str = Field("success", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now)

    @classmethod
    def success(cls, data: T = None, message: str = "success"):
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, code: int = 400, message: str = "error", data: T = None):
        return cls(code=code, message=message, data=data)


class PageResult(BaseModel, Generic[T]):
    items: List[T]
    page: int
    page_size: int
    total: int
    total_pages: int


class OperationLogResponse(BaseModel):
    id: int
    ticket_id: Optional[int]
    evaluation_id: Optional[int]
    operation_type: str
    operation_desc: str
    operation_detail: Optional[Dict[str, Any]]
    operator: Optional[str]
    operator_dept: Optional[str]
    operation_time: datetime

    class Config:
        from_attributes = True


class ReminderResponse(BaseModel):
    id: int
    ticket_id: int
    reminder_type: str
    reminder_level: Optional[str]
    reminder_time: datetime
    reminded_dept_name: Optional[str]
    reminded_user: Optional[str]
    content: Optional[str]
    is_escalation: bool
    escalated_to: Optional[str]
    sent_by_system: bool
    operator: Optional[str]
    read_status: bool

    class Config:
        from_attributes = True


class ArchiveResponse(BaseModel):
    id: int
    ticket_id: int
    archive_no: str
    archive_type: Optional[str]
    archive_time: datetime
    closing_statement: Optional[str]
    final_conclusion: Optional[str]
    citizen_satisfaction: Optional[str]
    archivist: Optional[str]
    retention_period: int
    is_permanent: bool

    class Config:
        from_attributes = True


class StatisticsOverview(BaseModel):
    total_evaluations: int = 0
    negative_evaluations: int = 0
    positive_evaluations: int = 0
    negative_rate: float = 0.0
    total_tickets: int = 0
    pending_tickets: int = 0
    processing_tickets: int = 0
    completed_tickets: int = 0
    overdue_tickets: int = 0
    completion_rate: float = 0.0
    average_processing_hours: float = 0.0
    citizen_satisfaction_rate: float = 0.0


class ProblemTypeStats(BaseModel):
    problem_type: str
    problem_type_desc: str
    count: int
    percentage: float


class DeptStats(BaseModel):
    dept_code: str
    dept_name: str
    total_tickets: int
    completed_tickets: int
    overdue_tickets: int
    average_processing_hours: float
    satisfaction_rate: float


class TimeSeriesStats(BaseModel):
    date: str
    total_evaluations: int
    negative_evaluations: int
    completed_tickets: int


class HighFrequencyProblem(BaseModel):
    problem_type: str
    problem_type_desc: str
    item_code: Optional[str]
    item_name: Optional[str]
    dept_code: Optional[str]
    dept_name: Optional[str]
    count: int
    trend: str
    typical_cases: List[Dict[str, Any]]
