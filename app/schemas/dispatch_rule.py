from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ItemMappingCreate(BaseModel):
    item_code: str = Field(..., max_length=64, description="事项编码（可自定义）")
    item_name: str = Field(..., max_length=255, description="事项名称")
    item_category: Optional[str] = None
    primary_dept_code: str = Field(..., description="主责部门编码")
    primary_dept_name: Optional[str] = None
    primary_dept_type: Optional[str] = None
    keywords: Optional[List[str]] = None
    is_active: bool = True


class ItemMappingUpdate(BaseModel):
    item_name: Optional[str] = None
    item_category: Optional[str] = None
    primary_dept_code: Optional[str] = None
    primary_dept_name: Optional[str] = None
    primary_dept_type: Optional[str] = None
    keywords: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ItemMappingResponse(BaseModel):
    id: int
    item_code: str
    item_name: str
    item_category: Optional[str]
    primary_dept_code: Optional[str]
    primary_dept_name: Optional[str]
    primary_dept_type: Optional[str]
    keywords: Optional[List] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DepartmentResponse(BaseModel):
    id: int
    dept_code: str
    dept_name: str
    dept_type: Optional[str]
    parent_code: Optional[str]
    level: int
    sort_order: int
    contact_person: Optional[str]
    contact_phone: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True
