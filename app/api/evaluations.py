from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.config.database import get_db
from app.schemas.common import ApiResponse, PageResult
from app.schemas.evaluation import (
    EvaluationCreate, EvaluationBatchCreate,
    EvaluationResponse, EvaluationDetailResponse, EvaluationQuery
)
from app.services.collection_service import CollectionService
from app.core.enums import DataSource, EvaluationLevel

router = APIRouter(prefix="/api/evaluations", tags=["评价归集"])


@router.post("/receive", response_model=ApiResponse[EvaluationDetailResponse])
def receive_evaluation(data: EvaluationCreate, db: Session = Depends(get_db)):
    service = CollectionService(db)
    evaluation = service.receive_evaluation(data)
    detail = service.get_evaluation_with_detail(evaluation.id)
    return ApiResponse.success(data=detail)


@router.post("/receive/batch", response_model=ApiResponse[list])
def receive_batch_evaluations(data: EvaluationBatchCreate, db: Session = Depends(get_db)):
    service = CollectionService(db)
    evaluations = service.receive_batch_evaluations(data)
    return ApiResponse.success(data=evaluations, message=f"成功接收{len(evaluations)}条评价数据")


@router.get("/{evaluation_id}", response_model=ApiResponse[EvaluationDetailResponse])
def get_evaluation(evaluation_id: int, db: Session = Depends(get_db)):
    service = CollectionService(db)
    detail = service.get_evaluation_with_detail(evaluation_id)
    if not detail:
        raise HTTPException(status_code=404, detail="评价数据不存在")
    return ApiResponse.success(data=detail)


@router.get("/no/{evaluation_no}", response_model=ApiResponse[EvaluationDetailResponse])
def get_evaluation_by_no(evaluation_no: str, db: Session = Depends(get_db)):
    service = CollectionService(db)
    evaluation = service.get_evaluation_by_no(evaluation_no)
    if not evaluation:
        raise HTTPException(status_code=404, detail="评价数据不存在")
    detail = service.get_evaluation_with_detail(evaluation.id)
    return ApiResponse.success(data=detail)


@router.get("", response_model=ApiResponse[PageResult[EvaluationResponse]])
def query_evaluations(
    source: Optional[DataSource] = Query(None, description="数据来源"),
    level: Optional[EvaluationLevel] = Query(None, description="评价等级"),
    citizen_phone: Optional[str] = Query(None, description="群众电话"),
    item_code: Optional[str] = Query(None, description="事项编码"),
    dept_code: Optional[str] = Query(None, description="部门编码"),
    is_duplicate: Optional[bool] = Query(None, description="是否重复"),
    has_ticket: Optional[bool] = Query(None, description="是否有工单"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query_params = EvaluationQuery(
        source=source,
        level=level,
        citizen_phone=citizen_phone,
        item_code=item_code,
        dept_code=dept_code,
        is_duplicate=is_duplicate,
        has_ticket=has_ticket,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size
    )

    service = CollectionService(db)
    items, total = service.query_evaluations(query_params)
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


@router.get("/{evaluation_id}/duplicates", response_model=ApiResponse[list])
def get_duplicate_evaluations(evaluation_id: int, db: Session = Depends(get_db)):
    service = CollectionService(db)
    evaluation = service.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="评价数据不存在")

    duplicates = service.get_duplicate_evaluations(evaluation_id)
    return ApiResponse.success(data=duplicates)
