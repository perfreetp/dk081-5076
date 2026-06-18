from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.config.database import get_db
from app.schemas.common import ApiResponse, PageResult, OperationLogResponse, ReminderResponse, ArchiveResponse
from app.schemas.ticket import (
    TicketAssign, TicketAccept, TicketReject,
    TicketProcess, TicketFeedback, TicketReview,
    TicketComplete, TicketResponse, TicketDetailResponse,
    TicketQuery, TicketStatusResponse
)
from app.services.ticket_service import TicketService
from app.services.dispatch_service import DispatchService
from app.services.reminder_service import ReminderService
from app.services.archive_service import ArchiveService
from app.services.trail_service import TrailService
from app.services.collection_service import CollectionService
from app.core.enums import TicketStatus, ProblemType, UrgencyLevel, ReminderType

router = APIRouter(prefix="/api/tickets", tags=["工单管理"])


@router.get("/{ticket_id}", response_model=ApiResponse[TicketDetailResponse])
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    service = TicketService(db)
    detail = service.get_ticket_with_detail(ticket_id)
    if not detail:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ApiResponse.success(data=detail)


@router.get("/no/{ticket_no}", response_model=ApiResponse[TicketDetailResponse])
def get_ticket_by_no(ticket_no: str, db: Session = Depends(get_db)):
    service = TicketService(db)
    detail = service.get_ticket_by_no_with_detail(ticket_no)
    if not detail:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ApiResponse.success(data=detail)


@router.get("/status/{ticket_no}", response_model=ApiResponse[TicketStatusResponse])
def get_ticket_status(ticket_no: str, db: Session = Depends(get_db)):
    service = TicketService(db)
    status_info = service.get_ticket_status(ticket_no)
    if not status_info:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ApiResponse.success(data=TicketStatusResponse(**status_info))


@router.get("", response_model=ApiResponse[PageResult[TicketResponse]])
def query_tickets(
    status: Optional[TicketStatus] = Query(None, description="工单状态"),
    problem_type: Optional[ProblemType] = Query(None, description="问题类型"),
    urgency_level: Optional[UrgencyLevel] = Query(None, description="紧急程度"),
    assigned_dept_code: Optional[str] = Query(None, description="责任部门编码"),
    citizen_phone: Optional[str] = Query(None, description="群众电话"),
    item_code: Optional[str] = Query(None, description="事项编码"),
    is_escalated: Optional[bool] = Query(None, description="是否升级"),
    is_overdue: Optional[bool] = Query(None, description="是否超时"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query_params = TicketQuery(
        status=status,
        problem_type=problem_type,
        urgency_level=urgency_level,
        assigned_dept_code=assigned_dept_code,
        citizen_phone=citizen_phone,
        item_code=item_code,
        is_escalated=is_escalated,
        is_overdue=is_overdue,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size
    )

    service = TicketService(db)
    items, total = service.query_tickets(query_params)
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse.success(
        data=PageResult(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages
        )
    )


@router.post("/assign", response_model=ApiResponse)
def assign_ticket(data: TicketAssign, db: Session = Depends(get_db)):
    service = DispatchService(db)
    assignment = service.manual_dispatch(data, operator="admin")
    if not assignment:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ApiResponse.success(message="工单分派成功")


@router.post("/accept", response_model=ApiResponse)
def accept_ticket(data: TicketAccept, db: Session = Depends(get_db)):
    service = DispatchService(db)
    success = service.accept_ticket(data.ticket_id, data.accept_user)
    if not success:
        raise HTTPException(status_code=400, detail="工单状态不允许接单或工单不存在")
    return ApiResponse.success(message="工单接单成功")


@router.post("/reject", response_model=ApiResponse)
def reject_ticket(data: TicketReject, db: Session = Depends(get_db)):
    service = DispatchService(db)
    success = service.reject_ticket(data.ticket_id, data.reject_reason, data.reject_user)
    if not success:
        raise HTTPException(status_code=400, detail="工单状态不允许拒收或工单不存在")
    return ApiResponse.success(message="工单拒收成功")


@router.post("/process", response_model=ApiResponse)
def process_ticket(data: TicketProcess, db: Session = Depends(get_db)):
    service = TicketService(db)
    success = service.process_ticket(data, operator=data.handler)
    if not success:
        raise HTTPException(status_code=400, detail="工单状态不允许处理或工单不存在")
    return ApiResponse.success(message="处理进度更新成功")


@router.post("/feedback", response_model=ApiResponse)
def submit_feedback(data: TicketFeedback, db: Session = Depends(get_db)):
    service = TicketService(db)
    success = service.submit_feedback(data, operator=data.handler)
    if not success:
        raise HTTPException(status_code=400, detail="工单状态不允许反馈或工单不存在")
    return ApiResponse.success(message="处理结果提交成功")


@router.post("/review", response_model=ApiResponse)
def review_ticket(data: TicketReview, db: Session = Depends(get_db)):
    service = TicketService(db)
    success = service.review_ticket(data, operator=data.reviewer)
    if not success:
        raise HTTPException(status_code=400, detail="工单状态不允许复核或工单不存在")
    return ApiResponse.success(message=f"复核{'通过' if data.is_passed else '不通过'}")


@router.post("/complete", response_model=ApiResponse[ArchiveResponse])
def complete_ticket(data: TicketComplete, db: Session = Depends(get_db)):
    service = TicketService(db)
    success = service.complete_ticket(data, operator="admin")
    if not success:
        raise HTTPException(status_code=400, detail="工单办结失败或工单不存在")

    archive_service = ArchiveService(db)
    archive = archive_service.get_archive_by_ticket(data.ticket_id)
    return ApiResponse.success(data=archive, message="工单办结成功")


@router.post("/{ticket_id}/remind", response_model=ApiResponse[ReminderResponse])
def manual_remind(
    ticket_id: int,
    content: str,
    reminder_type: ReminderType = ReminderType.FEEDBACK_TIMEOUT,
    db: Session = Depends(get_db)
):
    service = ReminderService(db)
    reminder = service.manual_reminder(ticket_id, content, "admin", reminder_type)
    if not reminder:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ApiResponse.success(data=reminder, message="催办通知发送成功")


@router.post("/{ticket_id}/escalate", response_model=ApiResponse[ReminderResponse])
def manual_escalate(
    ticket_id: int,
    escalated_to: str,
    reason: str,
    db: Session = Depends(get_db)
):
    service = ReminderService(db)
    reminder = service.manual_escalate(ticket_id, escalated_to, reason, "admin")
    if not reminder:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ApiResponse.success(data=reminder, message="升级报送成功")


@router.get("/{ticket_id}/trail", response_model=ApiResponse[list[OperationLogResponse]])
def get_ticket_trail(ticket_id: int, db: Session = Depends(get_db)):
    service = TrailService(db)
    logs = service.get_ticket_trail(ticket_id)
    return ApiResponse.success(data=logs)


@router.get("/{ticket_id}/reminders", response_model=ApiResponse[list[ReminderResponse]])
def get_ticket_reminders(ticket_id: int, db: Session = Depends(get_db)):
    service = ReminderService(db)
    reminders = service.get_ticket_reminders(ticket_id)
    return ApiResponse.success(data=reminders)


@router.get("/{ticket_id}/evaluations", response_model=ApiResponse[list])
def get_ticket_evaluations(ticket_id: int, db: Session = Depends(get_db)):
    service = TicketService(db)
    evaluations = service.get_ticket_evaluations(ticket_id)
    return ApiResponse.success(data=evaluations)


@router.get("/{ticket_id}/archive", response_model=ApiResponse[ArchiveResponse])
def get_ticket_archive(ticket_id: int, db: Session = Depends(get_db)):
    service = ArchiveService(db)
    archive = service.get_archive_by_ticket(ticket_id)
    if not archive:
        raise HTTPException(status_code=404, detail="归档记录不存在")
    return ApiResponse.success(data=archive)


@router.post("/{ticket_id}/reopen", response_model=ApiResponse)
def reopen_ticket(ticket_id: int, reason: str, db: Session = Depends(get_db)):
    service = TicketService(db)
    success = service.reopen_ticket(ticket_id, reason, "admin")
    if not success:
        raise HTTPException(status_code=400, detail="工单状态不允许重新打开或工单不存在")
    return ApiResponse.success(message="工单重新打开成功")


@router.post("/{ticket_id}/close", response_model=ApiResponse)
def close_ticket(ticket_id: int, reason: str, db: Session = Depends(get_db)):
    service = TicketService(db)
    success = service.close_ticket(ticket_id, reason, "admin")
    if not success:
        raise HTTPException(status_code=400, detail="工单关闭失败或工单不存在")
    return ApiResponse.success(message="工单关闭成功")
