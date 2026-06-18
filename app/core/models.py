from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.config.database import Base
from app.core.enums import (
    DataSource, EvaluationLevel, ProblemType, UrgencyLevel,
    TicketStatus, DepartmentType, ReminderType
)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_no = Column(String(64), unique=True, index=True, nullable=False)
    source = Column(String(32), nullable=False, index=True)
    level = Column(String(32), nullable=False, index=True)
    score = Column(Float, default=0)

    citizen_id = Column(String(64), index=True)
    citizen_name = Column(String(64))
    citizen_phone = Column(String(32), index=True)
    citizen_id_card = Column(String(32), index=True)

    item_code = Column(String(64), index=True)
    item_name = Column(String(255))
    item_category = Column(String(64))
    dept_code = Column(String(64), index=True)
    dept_name = Column(String(255))
    window_no = Column(String(32))
    handler_name = Column(String(64))

    content = Column(Text)
    suggestion = Column(Text)

    happen_time = Column(DateTime, index=True)
    evaluate_time = Column(DateTime, default=datetime.now, index=True)

    problem_type = Column(String(32))
    urgency_level = Column(String(32), default=UrgencyLevel.NORMAL)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, ForeignKey("evaluations.id"), nullable=True)

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    ticket = relationship("Ticket", back_populates="evaluations", foreign_keys=[ticket_id])
    duplicate_evaluations = relationship("Evaluation", backref="original_evaluation", remote_side=[id])
    operation_logs = relationship("OperationLog", back_populates="evaluation")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_no = Column(String(64), unique=True, index=True, nullable=False)

    status = Column(String(32), default=TicketStatus.PENDING, index=True)
    problem_type = Column(String(32), index=True)
    urgency_level = Column(String(32), default=UrgencyLevel.NORMAL, index=True)

    citizen_id = Column(String(64), index=True)
    citizen_name = Column(String(64))
    citizen_phone = Column(String(32))
    citizen_id_card = Column(String(32))

    item_code = Column(String(64))
    item_name = Column(String(255))
    item_category = Column(String(64))

    summary = Column(Text)
    content = Column(Text)

    assigned_dept_code = Column(String(64), index=True)
    assigned_dept_name = Column(String(255))
    assigned_dept_type = Column(String(32))
    assigned_user = Column(String(64))

    accept_time = Column(DateTime, nullable=True)
    deadline_time = Column(DateTime, nullable=True)
    first_reminder_time = Column(DateTime, nullable=True)
    last_reminder_time = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, default=0)

    handler = Column(String(64))
    handle_result = Column(Text)
    handle_measure = Column(Text)
    feedback_time = Column(DateTime, nullable=True)

    reviewer = Column(String(64))
    review_opinion = Column(Text)
    review_time = Column(DateTime, nullable=True)

    conclusion = Column(Text)
    closing_statement = Column(Text)
    completed_time = Column(DateTime, nullable=True)

    is_escalated = Column(Boolean, default=False)
    escalated_time = Column(DateTime, nullable=True)
    escalated_to = Column(String(255))
    escalation_reason = Column(Text)

    citizen_satisfaction = Column(String(32))
    is_satisfied = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    evaluations = relationship("Evaluation", back_populates="ticket", foreign_keys=[Evaluation.ticket_id])
    assignments = relationship("Assignment", back_populates="ticket")
    reminders = relationship("Reminder", back_populates="ticket")
    operation_logs = relationship("OperationLog", back_populates="ticket")
    archives = relationship("Archive", back_populates="ticket")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    from_dept_code = Column(String(64))
    from_dept_name = Column(String(255))
    from_user = Column(String(64))

    to_dept_code = Column(String(64), index=True)
    to_dept_name = Column(String(255))
    to_dept_type = Column(String(32))
    to_user = Column(String(64))

    assign_reason = Column(Text)
    assign_time = Column(DateTime, default=datetime.now)
    deadline = Column(DateTime)

    is_accepted = Column(Boolean, default=False)
    accept_time = Column(DateTime, nullable=True)
    accept_user = Column(String(64))

    is_rejected = Column(Boolean, default=False)
    reject_reason = Column(Text)
    reject_time = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.now)

    ticket = relationship("Ticket", back_populates="assignments")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    reminder_type = Column(String(32), index=True)
    reminder_level = Column(String(32))
    reminder_time = Column(DateTime, default=datetime.now)

    reminded_dept_code = Column(String(64))
    reminded_dept_name = Column(String(255))
    reminded_user = Column(String(64))

    content = Column(Text)
    is_escalation = Column(Boolean, default=False)
    escalated_to = Column(String(255))

    sent_by_system = Column(Boolean, default=True)
    operator = Column(String(64))

    read_status = Column(Boolean, default=False)
    read_time = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.now)

    ticket = relationship("Ticket", back_populates="reminders")


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), nullable=True)

    operation_type = Column(String(64), index=True)
    operation_desc = Column(String(255))
    operation_detail = Column(JSON)

    operator = Column(String(64))
    operator_dept = Column(String(255))
    operation_time = Column(DateTime, default=datetime.now, index=True)

    ip_address = Column(String(64))
    user_agent = Column(String(255))

    created_at = Column(DateTime, default=datetime.now)

    ticket = relationship("Ticket", back_populates="operation_logs")
    evaluation = relationship("Evaluation", back_populates="operation_logs")


class Archive(Base):
    __tablename__ = "archives"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    archive_no = Column(String(64), unique=True, index=True, nullable=False)

    archive_type = Column(String(32))
    archive_time = Column(DateTime, default=datetime.now, index=True)

    ticket_snapshot = Column(JSON)
    evaluations_snapshot = Column(JSON)
    operation_logs_snapshot = Column(JSON)
    reminders_snapshot = Column(JSON)
    assignments_snapshot = Column(JSON)

    closing_statement = Column(Text)
    final_conclusion = Column(Text)
    citizen_satisfaction = Column(String(32))

    archivist = Column(String(64))
    archive_remark = Column(Text)

    retention_period = Column(Integer, default=3650)
    is_permanent = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.now)

    ticket = relationship("Ticket", back_populates="archives")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    dept_code = Column(String(64), unique=True, index=True, nullable=False)
    dept_name = Column(String(255), nullable=False)
    dept_type = Column(String(32), index=True)

    parent_code = Column(String(64), index=True)
    level = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)

    contact_person = Column(String(64))
    contact_phone = Column(String(32))
    contact_email = Column(String(128))

    supervisor = Column(String(64))
    supervisor_phone = Column(String(32))

    item_codes = Column(JSON)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ItemMapping(Base):
    __tablename__ = "item_mappings"

    id = Column(Integer, primary_key=True, index=True)
    item_code = Column(String(64), unique=True, index=True, nullable=False)
    item_name = Column(String(255), nullable=False)
    item_category = Column(String(64), index=True)

    primary_dept_code = Column(String(64), index=True)
    primary_dept_name = Column(String(255))
    primary_dept_type = Column(String(32))

    support_dept_codes = Column(JSON)
    approval_dept_codes = Column(JSON)

    keywords = Column(JSON)
    problem_keywords = Column(JSON)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
