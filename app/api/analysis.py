from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.config.database import get_db
from app.schemas.common import (
    ApiResponse, StatisticsOverview, ProblemTypeStats,
    DeptStats, TimeSeriesStats, HighFrequencyProblem
)
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/analysis", tags=["统计分析"])


@router.get("/overview", response_model=ApiResponse[StatisticsOverview])
def get_overview(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: Session = Depends(get_db)
):
    service = AnalysisService(db)
    overview = service.get_overview(start_time, end_time)
    return ApiResponse.success(data=overview)


@router.get("/problem-types", response_model=ApiResponse[list[ProblemTypeStats]])
def get_problem_type_stats(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: Session = Depends(get_db)
):
    service = AnalysisService(db)
    stats = service.get_problem_type_stats(start_time, end_time)
    return ApiResponse.success(data=stats)


@router.get("/departments", response_model=ApiResponse[list[DeptStats]])
def get_dept_stats(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: Session = Depends(get_db)
):
    service = AnalysisService(db)
    stats = service.get_dept_stats(start_time, end_time)
    return ApiResponse.success(data=stats)


@router.get("/time-series", response_model=ApiResponse[list[TimeSeriesStats]])
def get_time_series_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db)
):
    service = AnalysisService(db)
    stats = service.get_time_series_stats(days)
    return ApiResponse.success(data=stats)


@router.get("/high-frequency", response_model=ApiResponse[list[HighFrequencyProblem]])
def get_high_frequency_problems(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    top_n: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db)
):
    service = AnalysisService(db)
    problems = service.get_high_frequency_problems(start_time, end_time, top_n)
    return ApiResponse.success(data=problems)


@router.get("/source-distribution", response_model=ApiResponse[list])
def get_source_distribution(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    db: Session = Depends(get_db)
):
    service = AnalysisService(db)
    distribution = service.get_source_distribution(start_time, end_time)
    return ApiResponse.success(data=distribution)


@router.get("/closing-statement/{ticket_no}", response_model=ApiResponse[str])
def get_closing_statement(
    ticket_no: str,
    db: Session = Depends(get_db)
):
    service = AnalysisService(db)
    statement = service.get_closing_statement(ticket_no)
    if not statement:
        return ApiResponse.error(code=404, message="工单不存在或尚未生成办结说明")
    return ApiResponse.success(data=statement)
