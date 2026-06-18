from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.config.database import get_db
from app.schemas.common import ApiResponse, PageResult, ArchiveResponse
from app.services.archive_service import ArchiveService

router = APIRouter(prefix="/api/archives", tags=["归档管理"])


@router.get("", response_model=ApiResponse[PageResult[ArchiveResponse]])
def query_archives(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    dept_code: Optional[str] = Query(None, description="部门编码"),
    problem_type: Optional[str] = Query(None, description="问题类型"),
    is_satisfied: Optional[bool] = Query(None, description="是否满意"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    service = ArchiveService(db)
    items, total = service.query_archives(
        start_time, end_time, dept_code, problem_type, is_satisfied, page, page_size
    )
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


@router.get("/{archive_id}", response_model=ApiResponse[ArchiveResponse])
def get_archive(archive_id: int, db: Session = Depends(get_db)):
    service = ArchiveService(db)
    archive = service.get_archive(archive_id)
    if not archive:
        raise HTTPException(status_code=404, detail="归档记录不存在")
    return ApiResponse.success(data=archive)


@router.get("/no/{archive_no}", response_model=ApiResponse[ArchiveResponse])
def get_archive_by_no(archive_no: str, db: Session = Depends(get_db)):
    service = ArchiveService(db)
    archive = service.get_archive_by_no(archive_no)
    if not archive:
        raise HTTPException(status_code=404, detail="归档记录不存在")
    return ApiResponse.success(data=archive)


@router.get("/ticket/{ticket_id}", response_model=ApiResponse[ArchiveResponse])
def get_archive_by_ticket(ticket_id: int, db: Session = Depends(get_db)):
    service = ArchiveService(db)
    archive = service.get_archive_by_ticket(ticket_id)
    if not archive:
        raise HTTPException(status_code=404, detail="归档记录不存在")
    return ApiResponse.success(data=archive)


@router.get("/{archive_id}/snapshot", response_model=ApiResponse[dict])
def get_archive_snapshot(archive_id: int, db: Session = Depends(get_db)):
    service = ArchiveService(db)
    archive = service.get_archive(archive_id)
    if not archive:
        raise HTTPException(status_code=404, detail="归档记录不存在")

    snapshot = {
        "archive_no": archive.archive_no,
        "archive_time": archive.archive_time,
        "ticket": archive.ticket_snapshot,
        "evaluations": archive.evaluations_snapshot,
        "operation_logs": archive.operation_logs_snapshot,
        "reminders": archive.reminders_snapshot,
        "assignments": archive.assignments_snapshot
    }
    return ApiResponse.success(data=snapshot)


@router.post("/auto-archive", response_model=ApiResponse[list[ArchiveResponse]])
def auto_archive_completed(
    days: int = Query(30, ge=1, description="完成多少天后自动归档"),
    db: Session = Depends(get_db)
):
    service = ArchiveService(db)
    archives = service.auto_archive_completed(days)
    return ApiResponse.success(
        data=archives,
        message=f"成功归档{len(archives)}条工单记录"
    )
