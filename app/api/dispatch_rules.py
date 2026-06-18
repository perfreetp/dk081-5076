from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.schemas.common import ApiResponse, PageResult
from app.schemas.dispatch_rule import (
    ItemMappingCreate, ItemMappingUpdate, ItemMappingResponse, DepartmentResponse
)
from app.core.models import ItemMapping, Department
from app.core.enums import DepartmentType

router = APIRouter(prefix="/api/dispatch-rules", tags=["分派规则管理"])


@router.get("/items", response_model=ApiResponse[PageResult[ItemMappingResponse]])
def list_item_mappings(
    item_name: Optional[str] = Query(None, description="事项名称（模糊）"),
    item_code: Optional[str] = Query(None, description="事项编码"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(ItemMapping)
    if item_name:
        q = q.filter(ItemMapping.item_name.like(f"%{item_name}%"))
    if item_code:
        q = q.filter(ItemMapping.item_code == item_code)
    if is_active is not None:
        q = q.filter(ItemMapping.is_active == is_active)

    total = q.count()
    items = q.order_by(ItemMapping.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size

    return ApiResponse.success(data=PageResult(
        items=items, page=page, page_size=page_size, total=total, total_pages=total_pages
    ))


@router.post("/items", response_model=ApiResponse[ItemMappingResponse])
def create_item_mapping(data: ItemMappingCreate, db: Session = Depends(get_db)):
    exists = db.query(ItemMapping).filter(ItemMapping.item_code == data.item_code).first()
    if exists:
        raise HTTPException(status_code=400, detail=f"事项编码[{data.item_code}]已存在")

    dept = db.query(Department).filter(Department.dept_code == data.primary_dept_code).first()
    dept_name = data.primary_dept_name
    dept_type = data.primary_dept_type
    if dept:
        dept_name = dept_name or dept.dept_name
        dept_type = dept_type or dept.dept_type

    mapping = ItemMapping(
        item_code=data.item_code,
        item_name=data.item_name,
        item_category=data.item_category,
        primary_dept_code=data.primary_dept_code,
        primary_dept_name=dept_name,
        primary_dept_type=dept_type,
        keywords=data.keywords,
        is_active=data.is_active
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return ApiResponse.success(data=mapping, message="事项映射创建成功")


@router.put("/items/{item_id}", response_model=ApiResponse[ItemMappingResponse])
def update_item_mapping(item_id: int, data: ItemMappingUpdate, db: Session = Depends(get_db)):
    mapping = db.query(ItemMapping).filter(ItemMapping.id == item_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="事项映射不存在")

    if data.primary_dept_code is not None and data.primary_dept_code != mapping.primary_dept_code:
        dept = db.query(Department).filter(Department.dept_code == data.primary_dept_code).first()
        if dept:
            mapping.primary_dept_name = data.primary_dept_name or dept.dept_name
            mapping.primary_dept_type = data.primary_dept_type or dept.dept_type

    update_fields = data.model_dump(exclude_unset=True)
    for k, v in update_fields.items():
        if k not in ("primary_dept_name", "primary_dept_type") or not getattr(mapping, "primary_dept_name", None):
            setattr(mapping, k, v)

    db.commit()
    db.refresh(mapping)
    return ApiResponse.success(data=mapping, message="事项映射更新成功")


@router.put("/items/{item_id}/deactivate", response_model=ApiResponse[ItemMappingResponse])
def deactivate_item_mapping(item_id: int, db: Session = Depends(get_db)):
    mapping = db.query(ItemMapping).filter(ItemMapping.id == item_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="事项映射不存在")
    mapping.is_active = False
    db.commit()
    db.refresh(mapping)
    return ApiResponse.success(data=mapping, message="事项映射已停用")


@router.put("/items/{item_id}/activate", response_model=ApiResponse[ItemMappingResponse])
def activate_item_mapping(item_id: int, db: Session = Depends(get_db)):
    mapping = db.query(ItemMapping).filter(ItemMapping.id == item_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="事项映射不存在")
    mapping.is_active = True
    db.commit()
    db.refresh(mapping)
    return ApiResponse.success(data=mapping, message="事项映射已启用")


@router.get("/departments", response_model=ApiResponse[list[DepartmentResponse]])
def list_departments(
    dept_type: Optional[str] = Query(None, description="部门类型"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    db: Session = Depends(get_db)
):
    q = db.query(Department)
    if dept_type:
        q = q.filter(Department.dept_type == dept_type)
    if is_active is not None:
        q = q.filter(Department.is_active == is_active)
    depts = q.order_by(Department.sort_order.asc(), Department.id.asc()).all()
    return ApiResponse.success(data=depts)
