from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from app.core.enums import DataSource, EvaluationLevel, ProblemType, UrgencyLevel, TicketStatus


class EvaluationCreate(BaseModel):
    evaluation_no: str = Field(..., max_length=64, description="评价单号")
    source: DataSource = Field(..., description="数据来源")
    level: EvaluationLevel = Field(..., description="评价等级")
    score: Optional[float] = Field(0, description="评分")

    citizen_id: Optional[str] = Field(None, max_length=64, description="群众ID")
    citizen_name: Optional[str] = Field(None, max_length=64, description="群众姓名")
    citizen_phone: Optional[str] = Field(None, max_length=32, description="联系电话")
    citizen_id_card: Optional[str] = Field(None, max_length=32, description="身份证号")

    item_code: Optional[str] = Field(None, max_length=64, description="事项编码")
    item_name: Optional[str] = Field(None, max_length=255, description="事项名称")
    item_category: Optional[str] = Field(None, max_length=64, description="事项分类")
    dept_code: Optional[str] = Field(None, max_length=64, description="部门编码")
    dept_name: Optional[str] = Field(None, max_length=255, description="部门名称")
    window_no: Optional[str] = Field(None, max_length=32, description="窗口号")
    handler_name: Optional[str] = Field(None, max_length=64, description="经办人姓名")

    content: Optional[str] = Field(None, description="评价内容")
    suggestion: Optional[str] = Field(None, description="建议")

    happen_time: Optional[datetime] = Field(None, description="事发时间")
    evaluate_time: Optional[datetime] = Field(None, description="评价时间")

    @field_validator('evaluate_time')
    def set_evaluate_time(cls, v):
        return v or datetime.now()


class EvaluationBatchCreate(BaseModel):
    evaluations: List[EvaluationCreate]
    source: DataSource


class EvaluationResponse(BaseModel):
    id: int
    evaluation_no: str
    source: str
    level: str
    score: float

    citizen_id: Optional[str]
    citizen_name: Optional[str]
    citizen_phone: Optional[str]

    item_code: Optional[str]
    item_name: Optional[str]
    dept_code: Optional[str]
    dept_name: Optional[str]

    problem_type: Optional[str]
    urgency_level: str
    is_duplicate: bool
    ticket_id: Optional[int]

    happen_time: Optional[datetime]
    evaluate_time: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class TicketAssignmentInfo(BaseModel):
    id: int
    to_dept_code: str
    to_dept_name: str
    to_dept_type: str
    to_user: Optional[str]
    assign_time: datetime
    deadline: Optional[datetime]
    assign_reason: Optional[str] = None
    dispatch_path: Optional[str] = None

    class Config:
        from_attributes = True


class EvaluationTicketInfo(BaseModel):
    id: int
    ticket_no: str
    status: str
    problem_type: str
    urgency_level: str
    assigned_dept_code: Optional[str]
    assigned_dept_name: Optional[str]
    assigned_dept_type: Optional[str]
    deadline_time: Optional[datetime]
    dispatch_path: Optional[str] = None
    latest_assignment: Optional[TicketAssignmentInfo] = None

    class Config:
        from_attributes = True


class EvaluationDetailResponse(EvaluationResponse):
    content: Optional[str]
    suggestion: Optional[str]
    item_category: Optional[str]
    window_no: Optional[str]
    handler_name: Optional[str]
    citizen_id_card: Optional[str]
    duplicate_of: Optional[int]
    updated_at: datetime
    ticket_info: Optional[EvaluationTicketInfo] = None
    duplicate_evaluations: Optional[List[dict]] = None


class EvaluationQuery(BaseModel):
    source: Optional[DataSource] = None
    level: Optional[EvaluationLevel] = None
    problem_type: Optional[ProblemType] = None
    urgency_level: Optional[UrgencyLevel] = None
    is_duplicate: Optional[bool] = None
    has_ticket: Optional[bool] = None
    citizen_phone: Optional[str] = None
    item_code: Optional[str] = None
    dept_code: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 20
