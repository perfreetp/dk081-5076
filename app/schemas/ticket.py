from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.core.enums import TicketStatus, ProblemType, UrgencyLevel, DepartmentType, DataSource


class TicketCreate(BaseModel):
    ticket_no: str = Field(..., max_length=64)
    problem_type: ProblemType
    urgency_level: UrgencyLevel = UrgencyLevel.NORMAL

    citizen_id: Optional[str] = None
    citizen_name: Optional[str] = None
    citizen_phone: Optional[str] = None
    citizen_id_card: Optional[str] = None

    item_code: Optional[str] = None
    item_name: Optional[str] = None
    item_category: Optional[str] = None

    summary: Optional[str] = None
    content: Optional[str] = None

    evaluation_ids: Optional[List[int]] = None


class TicketAssign(BaseModel):
    ticket_id: int
    dept_code: str
    dept_name: str
    dept_type: DepartmentType
    assign_user: Optional[str] = None
    assign_reason: Optional[str] = None
    deadline: Optional[datetime] = None


class TicketAccept(BaseModel):
    ticket_id: int
    accept_user: str


class TicketReject(BaseModel):
    ticket_id: int
    reject_reason: str
    reject_user: str


class TicketProcess(BaseModel):
    ticket_id: int
    handler: str
    handle_result: Optional[str] = None
    handle_measure: Optional[str] = None
    status: str = "processing"


class TicketFeedback(BaseModel):
    ticket_id: int
    handle_result: str
    handle_measure: str
    handler: str
    feedback_time: Optional[datetime] = None


class TicketReview(BaseModel):
    ticket_id: int
    reviewer: str
    review_opinion: str
    is_passed: bool
    citizen_satisfaction: Optional[str] = None


class TicketComplete(BaseModel):
    ticket_id: int
    conclusion: str
    closing_statement: str
    citizen_satisfaction: Optional[str] = None
    is_satisfied: bool = False


class TicketEscalate(BaseModel):
    ticket_id: int
    escalated_to: str
    escalation_reason: str
    operator: str


class TicketResponse(BaseModel):
    id: int
    ticket_no: str
    status: str
    problem_type: str
    urgency_level: str

    citizen_name: Optional[str]
    citizen_phone: Optional[str]

    item_code: Optional[str]
    item_name: Optional[str]
    item_category: Optional[str]

    summary: Optional[str]
    content: Optional[str]

    assigned_dept_code: Optional[str]
    assigned_dept_name: Optional[str]
    assigned_dept_type: Optional[str]

    accept_time: Optional[datetime]
    deadline_time: Optional[datetime]
    reminder_count: int

    handler: Optional[str]
    handle_result: Optional[str]
    feedback_time: Optional[datetime]

    reviewer: Optional[str]
    review_opinion: Optional[str]
    review_time: Optional[datetime]

    conclusion: Optional[str]
    closing_statement: Optional[str]
    completed_time: Optional[datetime]

    is_escalated: bool
    escalated_time: Optional[datetime]
    escalated_to: Optional[str]

    citizen_satisfaction: Optional[str]
    is_satisfied: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TicketEvaluationInfo(BaseModel):
    id: int
    evaluation_no: str
    source: str
    source_desc: str
    level: str
    content: Optional[str]
    evaluate_time: datetime
    is_duplicate: bool
    is_original: bool
    role: str = "original"
    citizen_name: Optional[str] = None
    citizen_phone: Optional[str] = None

    class Config:
        from_attributes = True


class MergedEvaluationSummary(BaseModel):
    original_evaluation: Optional[TicketEvaluationInfo] = None
    merged_evaluations: List[TicketEvaluationInfo] = []
    total_count: int = 0
    source_channels: List[str] = []
    first_time: Optional[datetime] = None
    last_time: Optional[datetime] = None
    timeline: List[TicketEvaluationInfo] = []


class TicketAssignmentHistory(BaseModel):
    id: int
    from_dept_code: Optional[str]
    from_dept_name: Optional[str]
    to_dept_code: str
    to_dept_name: str
    to_dept_type: str
    to_user: Optional[str]
    assign_reason: Optional[str]
    assign_time: datetime
    deadline: Optional[datetime]
    dispatch_path: Optional[str]
    dispatch_path_desc: Optional[str]
    is_accepted: bool
    accept_time: Optional[datetime]
    is_rejected: bool
    reject_reason: Optional[str]
    reject_time: Optional[datetime]

    class Config:
        from_attributes = True


class TicketOperationLog(BaseModel):
    id: int
    operation_type: str
    operation_desc: str
    operation_detail: Optional[Dict[str, Any]]
    operator: str
    operator_dept: Optional[str]
    operation_time: datetime

    class Config:
        from_attributes = True


class TicketDetailResponse(TicketResponse):
    handle_measure: Optional[str]
    escalation_reason: Optional[str]
    citizen_id: Optional[str]
    citizen_id_card: Optional[str]
    assigned_user: Optional[str]
    first_reminder_time: Optional[datetime]
    last_reminder_time: Optional[datetime]
    dispatch_path: Optional[str] = None
    dispatch_path_desc: Optional[str] = None
    latest_assignment: Optional[TicketAssignmentHistory] = None
    assignment_history: Optional[List[TicketAssignmentHistory]] = None
    related_evaluations: Optional[List[TicketEvaluationInfo]] = None
    merged_summary: Optional[MergedEvaluationSummary] = None
    operation_trail: Optional[List[TicketOperationLog]] = None


class TicketQuery(BaseModel):
    status: Optional[TicketStatus] = None
    problem_type: Optional[ProblemType] = None
    urgency_level: Optional[UrgencyLevel] = None
    assigned_dept_code: Optional[str] = None
    citizen_phone: Optional[str] = None
    item_code: Optional[str] = None
    is_escalated: Optional[bool] = None
    is_overdue: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


class TicketStatusResponse(BaseModel):
    ticket_no: str
    status: str
    status_desc: str
    current_step: str
    handler: Optional[str]
    deadline_time: Optional[datetime]
    remaining_hours: Optional[float]
    is_overdue: bool
    closing_statement: Optional[str]
    citizen_satisfaction: Optional[str]
