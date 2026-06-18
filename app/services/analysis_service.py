from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict

from app.core.models import Evaluation, Ticket, Archive, Department
from app.core.enums import (
    EvaluationLevel, TicketStatus, ProblemType,
    UrgencyLevel, DataSource
)
from app.schemas.common import (
    StatisticsOverview, ProblemTypeStats, DeptStats,
    TimeSeriesStats, HighFrequencyProblem
)


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self, start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> StatisticsOverview:
        if not start_time:
            start_time = datetime.now() - timedelta(days=30)
        if not end_time:
            end_time = datetime.now()

        total_evaluations = self.db.query(Evaluation).filter(
            Evaluation.evaluate_time >= start_time,
            Evaluation.evaluate_time <= end_time
        ).count()

        negative_evaluations = self.db.query(Evaluation).filter(
            Evaluation.evaluate_time >= start_time,
            Evaluation.evaluate_time <= end_time,
            Evaluation.level.in_([EvaluationLevel.POOR, EvaluationLevel.VERY_POOR])
        ).count()

        positive_evaluations = self.db.query(Evaluation).filter(
            Evaluation.evaluate_time >= start_time,
            Evaluation.evaluate_time <= end_time,
            Evaluation.level.in_([EvaluationLevel.EXCELLENT, EvaluationLevel.GOOD])
        ).count()

        total_tickets = self.db.query(Ticket).filter(
            Ticket.created_at >= start_time,
            Ticket.created_at <= end_time
        ).count()

        pending_tickets = self.db.query(Ticket).filter(
            Ticket.created_at >= start_time,
            Ticket.created_at <= end_time,
            Ticket.status.in_([TicketStatus.PENDING, TicketStatus.ASSIGNED])
        ).count()

        processing_tickets = self.db.query(Ticket).filter(
            Ticket.created_at >= start_time,
            Ticket.created_at <= end_time,
            Ticket.status.in_([TicketStatus.ACCEPTED, TicketStatus.PROCESSING, TicketStatus.FEEDBACK])
        ).count()

        completed_tickets = self.db.query(Ticket).filter(
            Ticket.created_at >= start_time,
            Ticket.created_at <= end_time,
            Ticket.status.in_([TicketStatus.COMPLETED, TicketStatus.CLOSED])
        ).count()

        now = datetime.now()
        overdue_tickets = self.db.query(Ticket).filter(
            Ticket.status.in_([
                TicketStatus.ASSIGNED, TicketStatus.ACCEPTED, TicketStatus.PROCESSING
            ]),
            Ticket.deadline_time <= now
        ).count()

        negative_rate = (negative_evaluations / total_evaluations * 100) if total_evaluations > 0 else 0.0
        completion_rate = (completed_tickets / total_tickets * 100) if total_tickets > 0 else 0.0

        avg_hours = self._calculate_average_processing_hours(start_time, end_time)

        satisfied_count = self.db.query(Ticket).filter(
            Ticket.created_at >= start_time,
            Ticket.created_at <= end_time,
            Ticket.status.in_([TicketStatus.COMPLETED, TicketStatus.CLOSED]),
            Ticket.is_satisfied == True
        ).count()
        completed_with_satisfaction = self.db.query(Ticket).filter(
            Ticket.created_at >= start_time,
            Ticket.created_at <= end_time,
            Ticket.status.in_([TicketStatus.COMPLETED, TicketStatus.CLOSED]),
            Ticket.citizen_satisfaction.isnot(None)
        ).count()
        satisfaction_rate = (satisfied_count / completed_with_satisfaction * 100) if completed_with_satisfaction > 0 else 0.0

        return StatisticsOverview(
            total_evaluations=total_evaluations,
            negative_evaluations=negative_evaluations,
            positive_evaluations=positive_evaluations,
            negative_rate=round(negative_rate, 2),
            total_tickets=total_tickets,
            pending_tickets=pending_tickets,
            processing_tickets=processing_tickets,
            completed_tickets=completed_tickets,
            overdue_tickets=overdue_tickets,
            completion_rate=round(completion_rate, 2),
            average_processing_hours=round(avg_hours, 2),
            citizen_satisfaction_rate=round(satisfaction_rate, 2)
        )

    def _calculate_average_processing_hours(self, start_time: datetime, end_time: datetime) -> float:
        completed = self.db.query(Ticket).filter(
            Ticket.created_at >= start_time,
            Ticket.created_at <= end_time,
            Ticket.status.in_([TicketStatus.COMPLETED, TicketStatus.CLOSED]),
            Ticket.completed_time.isnot(None)
        ).all()

        if not completed:
            return 0.0

        total_hours = 0.0
        for ticket in completed:
            if ticket.completed_time and ticket.created_at:
                delta = ticket.completed_time - ticket.created_at
                total_hours += delta.total_seconds() / 3600

        return total_hours / len(completed)

    def get_problem_type_stats(self, start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None) -> List[ProblemTypeStats]:
        if not start_time:
            start_time = datetime.now() - timedelta(days=30)
        if not end_time:
            end_time = datetime.now()

        results = self.db.query(
            Ticket.problem_type,
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.created_at >= start_time,
            Ticket.created_at <= end_time
        ).group_by(Ticket.problem_type).all()

        total = sum(r.count for r in results) if results else 0

        stats = []
        for problem_type, count in results:
            percentage = (count / total * 100) if total > 0 else 0.0
            stats.append(ProblemTypeStats(
                problem_type=problem_type or ProblemType.OTHER,
                problem_type_desc=ProblemType.get_description(problem_type or ProblemType.OTHER),
                count=count,
                percentage=round(percentage, 2)
            ))

        stats.sort(key=lambda x: x.count, reverse=True)
        return stats

    def get_dept_stats(self, start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None) -> List[DeptStats]:
        if not start_time:
            start_time = datetime.now() - timedelta(days=30)
        if not end_time:
            end_time = datetime.now()

        dept_codes = self.db.query(Ticket.assigned_dept_code).filter(
            Ticket.created_at >= start_time,
            Ticket.created_at <= end_time,
            Ticket.assigned_dept_code.isnot(None)
        ).distinct().all()

        stats = []
        now = datetime.now()

        for (dept_code,) in dept_codes:
            if not dept_code:
                continue

            dept = self.db.query(Department).filter(
                Department.dept_code == dept_code
            ).first()
            dept_name = dept.dept_name if dept else dept_code

            total = self.db.query(Ticket).filter(
                Ticket.created_at >= start_time,
                Ticket.created_at <= end_time,
                Ticket.assigned_dept_code == dept_code
            ).count()

            completed = self.db.query(Ticket).filter(
                Ticket.created_at >= start_time,
                Ticket.created_at <= end_time,
                Ticket.assigned_dept_code == dept_code,
                Ticket.status.in_([TicketStatus.COMPLETED, TicketStatus.CLOSED])
            ).count()

            overdue = self.db.query(Ticket).filter(
                Ticket.assigned_dept_code == dept_code,
                Ticket.status.in_([TicketStatus.ASSIGNED, TicketStatus.ACCEPTED, TicketStatus.PROCESSING]),
                Ticket.deadline_time <= now
            ).count()

            completed_tickets = self.db.query(Ticket).filter(
                Ticket.created_at >= start_time,
                Ticket.created_at <= end_time,
                Ticket.assigned_dept_code == dept_code,
                Ticket.status.in_([TicketStatus.COMPLETED, TicketStatus.CLOSED]),
                Ticket.completed_time.isnot(None)
            ).all()

            avg_hours = 0.0
            if completed_tickets:
                total_hours = sum(
                    (t.completed_time - t.created_at).total_seconds() / 3600
                    for t in completed_tickets if t.completed_time and t.created_at
                )
                avg_hours = total_hours / len(completed_tickets)

            satisfied = self.db.query(Ticket).filter(
                Ticket.created_at >= start_time,
                Ticket.created_at <= end_time,
                Ticket.assigned_dept_code == dept_code,
                Ticket.status.in_([TicketStatus.COMPLETED, TicketStatus.CLOSED]),
                Ticket.is_satisfied == True
            ).count()
            completed_with_satisfaction = self.db.query(Ticket).filter(
                Ticket.created_at >= start_time,
                Ticket.created_at <= end_time,
                Ticket.assigned_dept_code == dept_code,
                Ticket.status.in_([TicketStatus.COMPLETED, TicketStatus.CLOSED]),
                Ticket.citizen_satisfaction.isnot(None)
            ).count()
            satisfaction_rate = (satisfied / completed_with_satisfaction * 100) if completed_with_satisfaction > 0 else 0.0

            stats.append(DeptStats(
                dept_code=dept_code,
                dept_name=dept_name,
                total_tickets=total,
                completed_tickets=completed,
                overdue_tickets=overdue,
                average_processing_hours=round(avg_hours, 2),
                satisfaction_rate=round(satisfaction_rate, 2)
            ))

        stats.sort(key=lambda x: x.total_tickets, reverse=True)
        return stats

    def get_time_series_stats(self, days: int = 30) -> List[TimeSeriesStats]:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        stats = []
        for i in range(days):
            day_start = (start_time + timedelta(days=i)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = day_start + timedelta(days=1)

            total_eval = self.db.query(Evaluation).filter(
                Evaluation.evaluate_time >= day_start,
                Evaluation.evaluate_time < day_end
            ).count()

            negative_eval = self.db.query(Evaluation).filter(
                Evaluation.evaluate_time >= day_start,
                Evaluation.evaluate_time < day_end,
                Evaluation.level.in_([EvaluationLevel.POOR, EvaluationLevel.VERY_POOR])
            ).count()

            completed = self.db.query(Ticket).filter(
                Ticket.completed_time >= day_start,
                Ticket.completed_time < day_end,
                Ticket.status.in_([TicketStatus.COMPLETED, TicketStatus.CLOSED])
            ).count()

            stats.append(TimeSeriesStats(
                date=day_start.strftime('%Y-%m-%d'),
                total_evaluations=total_eval,
                negative_evaluations=negative_eval,
                completed_tickets=completed
            ))

        return stats

    def get_high_frequency_problems(self, start_time: Optional[datetime] = None,
                                   end_time: Optional[datetime] = None,
                                   top_n: int = 10) -> List[HighFrequencyProblem]:
        if not start_time:
            start_time = datetime.now() - timedelta(days=90)
        if not end_time:
            end_time = datetime.now()

        mid_time = start_time + (end_time - start_time) / 2

        recent_start = mid_time
        earlier_start = start_time
        earlier_end = mid_time

        results = self.db.query(
            Ticket.problem_type,
            Ticket.item_code,
            Ticket.item_name,
            Ticket.assigned_dept_code,
            Ticket.assigned_dept_name,
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.created_at >= start_time,
            Ticket.created_at <= end_time
        ).group_by(
            Ticket.problem_type,
            Ticket.item_code,
            Ticket.item_name,
            Ticket.assigned_dept_code,
            Ticket.assigned_dept_name
        ).order_by(func.count(Ticket.id).desc()).limit(top_n).all()

        problems = []
        for problem_type, item_code, item_name, dept_code, dept_name, count in results:
            recent_count = self.db.query(Ticket).filter(
                Ticket.created_at >= recent_start,
                Ticket.created_at <= end_time,
                Ticket.problem_type == problem_type,
                (Ticket.item_code == item_code) if item_code else True,
                (Ticket.assigned_dept_code == dept_code) if dept_code else True
            ).count()

            earlier_count = self.db.query(Ticket).filter(
                Ticket.created_at >= earlier_start,
                Ticket.created_at < earlier_end,
                Ticket.problem_type == problem_type,
                (Ticket.item_code == item_code) if item_code else True,
                (Ticket.assigned_dept_code == dept_code) if dept_code else True
            ).count()

            if earlier_count > 0:
                change_pct = ((recent_count - earlier_count) / earlier_count) * 100
                if change_pct > 20:
                    trend = "上升"
                elif change_pct < -20:
                    trend = "下降"
                else:
                    trend = "平稳"
            else:
                trend = "新增"

            typical_cases = self.db.query(Ticket).filter(
                Ticket.created_at >= start_time,
                Ticket.created_at <= end_time,
                Ticket.problem_type == problem_type,
                (Ticket.item_code == item_code) if item_code else True,
                (Ticket.assigned_dept_code == dept_code) if dept_code else True
            ).order_by(Ticket.created_at.desc()).limit(3).all()

            cases = []
            for case in typical_cases:
                cases.append({
                    "ticket_no": case.ticket_no,
                    "summary": case.summary,
                    "citizen_name": case.citizen_name,
                    "created_at": case.created_at.strftime('%Y-%m-%d %H:%M') if case.created_at else None,
                    "status": TicketStatus.get_description(case.status)
                })

            problems.append(HighFrequencyProblem(
                problem_type=problem_type or ProblemType.OTHER,
                problem_type_desc=ProblemType.get_description(problem_type or ProblemType.OTHER),
                item_code=item_code,
                item_name=item_name,
                dept_code=dept_code,
                dept_name=dept_name,
                count=count,
                trend=trend,
                typical_cases=cases
            ))

        return problems

    def get_source_distribution(self, start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        if not start_time:
            start_time = datetime.now() - timedelta(days=30)
        if not end_time:
            end_time = datetime.now()

        results = self.db.query(
            Evaluation.source,
            Evaluation.level,
            func.count(Evaluation.id).label('count')
        ).filter(
            Evaluation.evaluate_time >= start_time,
            Evaluation.evaluate_time <= end_time
        ).group_by(Evaluation.source, Evaluation.level).all()

        source_data = defaultdict(lambda: {"total": 0, "negative": 0, "positive": 0})
        for source, level, count in results:
            source_data[source]["total"] += count
            if level in [EvaluationLevel.POOR, EvaluationLevel.VERY_POOR]:
                source_data[source]["negative"] += count
            elif level in [EvaluationLevel.EXCELLENT, EvaluationLevel.GOOD]:
                source_data[source]["positive"] += count

        distribution = []
        for source, data in source_data.items():
            distribution.append({
                "source": source,
                "source_desc": DataSource.get_description(source),
                "total": data["total"],
                "negative": data["negative"],
                "positive": data["positive"],
                "negative_rate": round((data["negative"] / data["total"] * 100), 2) if data["total"] > 0 else 0.0
            })

        distribution.sort(key=lambda x: x["total"], reverse=True)
        return distribution

    def get_closing_statement(self, ticket_no: str) -> Optional[str]:
        ticket = self.db.query(Ticket).filter(Ticket.ticket_no == ticket_no).first()
        if not ticket:
            return None
        return ticket.closing_statement
