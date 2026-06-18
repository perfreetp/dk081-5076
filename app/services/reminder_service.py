from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from app.core.models import Ticket, Reminder, Department, Assignment
from app.core.enums import (
    ReminderType, TicketStatus, UrgencyLevel
)
from app.config.settings import settings
from app.services.trail_service import TrailService

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, db: Session):
        self.db = db
        self.trail_service = TrailService(db)

    def check_and_create_reminders(self) -> List[Reminder]:
        reminders = []

        reminders.extend(self._check_accept_timeout_reminders())
        reminders.extend(self._check_feedback_timeout_reminders())
        reminders.extend(self._check_review_timeout_reminders())
        reminders.extend(self._check_escalation_reminders())

        self.db.commit()
        return reminders

    def _check_accept_timeout_reminders(self) -> List[Reminder]:
        reminders = []

        accept_timeout = datetime.now() - timedelta(hours=settings.SUPERVISE_TIMEOUT_HOURS)

        tickets = self.db.query(Ticket).filter(
            Ticket.status == TicketStatus.ASSIGNED,
            or_(
                Ticket.first_reminder_time.is_(None),
                and_(
                    Ticket.last_reminder_time <= (datetime.now() - timedelta(hours=12))
                )
            )
        ).all()

        for ticket in tickets:
            latest_assignment = self.db.query(Assignment).filter(
                Assignment.ticket_id == ticket.id
            ).order_by(Assignment.assign_time.desc()).first()

            if not latest_assignment:
                continue

            if latest_assignment.assign_time > accept_timeout:
                continue

            hours_since_assign = (datetime.now() - latest_assignment.assign_time).total_seconds() / 3600

            reminder = self._create_reminder(
                ticket,
                ReminderType.ACCEPT_TIMEOUT,
                "接单超时催办",
                f"您有一个工单已于{latest_assignment.assign_time.strftime('%Y-%m-%d %H:%M')}分派，已超过{settings.SUPERVISE_TIMEOUT_HOURS}小时未接单，距分派已{hours_since_assign:.1f}小时，请尽快处理。"
            )
            if reminder:
                reminders.append(reminder)
                self._update_ticket_reminder_info(ticket, reminder)

        return reminders

    def _check_feedback_timeout_reminders(self) -> List[Reminder]:
        reminders = []

        tickets = self.db.query(Ticket).filter(
            Ticket.status.in_([TicketStatus.ACCEPTED, TicketStatus.PROCESSING]),
            Ticket.deadline_time <= datetime.now(),
            or_(
                Ticket.first_reminder_time.is_(None),
                and_(
                    Ticket.last_reminder_time <= (datetime.now() - timedelta(hours=24))
                )
            )
        ).all()

        for ticket in tickets:
            reminder = self._create_reminder(
                ticket,
                ReminderType.FEEDBACK_TIMEOUT,
                "反馈超时催办",
                "您负责的工单已超过办理期限，请尽快反馈处理结果。"
            )
            if reminder:
                reminders.append(reminder)
                self._update_ticket_reminder_info(ticket, reminder)

        return reminders

    def _check_review_timeout_reminders(self) -> List[Reminder]:
        reminders = []

        review_timeout = timedelta(hours=settings.REVIEW_TIMEOUT_HOURS)

        tickets = self.db.query(Ticket).filter(
            Ticket.status == TicketStatus.FEEDBACK,
            Ticket.feedback_time <= (datetime.now() - review_timeout),
            or_(
                Ticket.first_reminder_time.is_(None),
                and_(
                    Ticket.last_reminder_time <= (datetime.now() - timedelta(hours=24))
                )
            )
        ).all()

        for ticket in tickets:
            reminder = self._create_reminder(
                ticket,
                ReminderType.REVIEW_TIMEOUT,
                "复核超时催办",
                "您有一个工单已超过复核期限，请尽快完成复核。"
            )
            if reminder:
                reminders.append(reminder)
                self._update_ticket_reminder_info(ticket, reminder)

        return reminders

    def _check_escalation_reminders(self) -> List[Reminder]:
        reminders = []

        urgent_escalation_time = datetime.now() - timedelta(hours=settings.URGENT_UPGRADE_HOURS)
        major_escalation_time = datetime.now() - timedelta(hours=settings.MAJOR_UPGRADE_HOURS)

        tickets = self.db.query(Ticket).filter(
            Ticket.status.in_([
                TicketStatus.ASSIGNED,
                TicketStatus.ACCEPTED,
                TicketStatus.PROCESSING
            ]),
            Ticket.is_escalated == False
        ).all()

        for ticket in tickets:
            latest_assignment = self.db.query(Assignment).filter(
                Assignment.ticket_id == ticket.id
            ).order_by(Assignment.assign_time.desc()).first()

            base_time = latest_assignment.assign_time if latest_assignment else ticket.created_at

            should_escalate = False
            if ticket.urgency_level == UrgencyLevel.URGENT and base_time <= urgent_escalation_time:
                should_escalate = True
            elif ticket.urgency_level in [UrgencyLevel.MAJOR, UrgencyLevel.SENSITIVE] and base_time <= major_escalation_time:
                should_escalate = True

            if not should_escalate:
                continue

            hours_since_assign = (datetime.now() - base_time).total_seconds() / 3600

            reminder = self._create_reminder(
                ticket,
                ReminderType.ESCALATION,
                "升级报送",
                f"该工单为{UrgencyLevel.get_description(ticket.urgency_level)}级别，于{base_time.strftime('%Y-%m-%d %H:%M')}分派，已{hours_since_assign:.1f}小时未处理，现升级报送至营商环境督查室。",
                is_escalation=True,
                escalated_to="营商环境督查室"
            )
            if reminder:
                reminders.append(reminder)

                ticket.is_escalated = True
                ticket.escalated_time = datetime.now()
                ticket.escalated_to = "营商环境督查室"
                ticket.escalation_reason = f"{UrgencyLevel.get_description(ticket.urgency_level)}工单超时未处理，自动升级"
                ticket.status = TicketStatus.ESCALATED

                self.trail_service.log_ticket_operation(
                    ticket_id=ticket.id,
                    operation_type="auto_escalated",
                    operation_desc=f"自动升级报送至营商环境督查室",
                    operator="system",
                    detail={
                        "reason": ticket.escalation_reason,
                        "urgency_level": ticket.urgency_level,
                        "base_time": base_time.isoformat(),
                        "hours_since_assign": hours_since_assign
                    }
                )

        return reminders

    def _create_reminder(self, ticket: Ticket, reminder_type: str,
                          title: str, content: str,
                          is_escalation: bool = False,
                          escalated_to: Optional[str] = None) -> Optional[Reminder]:

        dept = self.db.query(Department).filter(
            Department.dept_code == ticket.assigned_dept_code
        ).first()

        reminder = Reminder(
            ticket_id=ticket.id,
            reminder_type=reminder_type,
            reminder_level=ticket.urgency_level,
            reminder_time=datetime.now(),
            reminded_dept_code=ticket.assigned_dept_code,
            reminded_dept_name=ticket.assigned_dept_name,
            reminded_user=ticket.assigned_user or (dept.contact_person if dept else None),
            content=f"【{title}】工单[{ticket.ticket_no}]\n{content}\n\n工单摘要：{ticket.summary}\n截止时间：{ticket.deadline_time.strftime('%Y-%m-%d %H:%M') if ticket.deadline_time else '无'}",
            is_escalation=is_escalation,
            escalated_to=escalated_to,
            sent_by_system=True
        )

        self.db.add(reminder)
        self.db.flush()

        return reminder

    def _update_ticket_reminder_info(self, ticket: Ticket, reminder: Reminder):
        if not ticket.first_reminder_time:
            ticket.first_reminder_time = reminder.reminder_time
        ticket.last_reminder_time = reminder.reminder_time
        ticket.reminder_count = (ticket.reminder_count or 0) + 1

        self.trail_service.log_ticket_operation(
            ticket_id=ticket.id,
            operation_type="reminder_sent",
            operation_desc=f"发送{ReminderType.get_description(reminder.reminder_type)}",
            operator="system",
            detail={
                "reminder_id": reminder.id,
                "reminder_count": ticket.reminder_count
            }
        )

    def manual_reminder(self, ticket_id: int, content: str, operator: str,
                         reminder_type: str = ReminderType.FEEDBACK_TIMEOUT) -> Optional[Reminder]:
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return None

        reminder = self._create_reminder(
            ticket,
            reminder_type,
            "人工催办",
            content,
            is_escalation=False
        )
        reminder.sent_by_system = False
        reminder.operator = operator

        self._update_ticket_reminder_info(ticket, reminder)

        self.db.commit()
        self.db.refresh(reminder)

        return reminder

    def manual_escalate(self, ticket_id: int, escalated_to: str,
                      reason: str, operator: str) -> Optional[Reminder]:
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return None

        reminder = self._create_reminder(
            ticket,
            ReminderType.ESCALATION,
            "人工升级报送",
            reason,
            is_escalation=True,
            escalated_to=escalated_to
        )
        reminder.sent_by_system = False
        reminder.operator = operator

        ticket.is_escalated = True
        ticket.escalated_time = datetime.now()
        ticket.escalated_to = escalated_to
        ticket.escalation_reason = reason
        ticket.status = TicketStatus.ESCALATED

        self.trail_service.log_ticket_operation(
            ticket_id=ticket.id,
            operation_type="manual_escalated",
            operation_desc=f"人工升级报送至{escalated_to}",
            operator=operator,
            detail={"reason": reason}
        )

        self.db.commit()
        self.db.refresh(reminder)

        return reminder

    def get_ticket_reminders(self, ticket_id: int) -> List[Reminder]:
        return self.db.query(Reminder).filter(
            Reminder.ticket_id == ticket_id
        ).order_by(Reminder.reminder_time.desc()).all()

    def get_pending_reminders(self, dept_code: Optional[str] = None,
                           unread_only: bool = False) -> List[Reminder]:
        q = self.db.query(Reminder)

        if dept_code:
            q = q.filter(Reminder.reminded_dept_code == dept_code)
        if unread_only:
            q = q.filter(Reminder.read_status == False)

        return q.order_by(Reminder.reminder_time.desc()).all()

    def mark_as_read(self, reminder_id: int) -> bool:
        reminder = self.db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder:
            reminder.read_status = True
            reminder.read_time = datetime.now()
            self.db.commit()
            return True
        return False

    def get_overdue_tickets(self) -> List[Ticket]:
        now = datetime.now()
        return self.db.query(Ticket).filter(
            Ticket.status.in_([
                TicketStatus.ASSIGNED,
                TicketStatus.ACCEPTED,
                TicketStatus.PROCESSING
            ]),
            Ticket.deadline_time <= now
        ).order_by(Ticket.deadline_time.asc()).all()
