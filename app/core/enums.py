from enum import Enum


class DataSource(str, Enum):
    HALL = "hall"
    APP = "app"
    HOTLINE_12345 = "12345"
    EVALUATOR = "evaluator"
    SMS = "sms"

    @classmethod
    def get_description(cls, source):
        descriptions = {
            cls.HALL: "政务大厅",
            cls.APP: "政务App",
            cls.HOTLINE_12345: "12345热线",
            cls.EVALUATOR: "评价器",
            cls.SMS: "短信回访"
        }
        return descriptions.get(source, "未知来源")


class EvaluationLevel(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    VERY_POOR = "very_poor"

    @classmethod
    def get_description(cls, level):
        descriptions = {
            cls.EXCELLENT: "非常满意",
            cls.GOOD: "满意",
            cls.AVERAGE: "基本满意",
            cls.POOR: "不满意",
            cls.VERY_POOR: "非常不满意"
        }
        return descriptions.get(level, "未知评价")

    @classmethod
    def is_negative(cls, level):
        return level in [cls.POOR, cls.VERY_POOR]


class ProblemType(str, Enum):
    SERVICE_ATTITUDE = "service_attitude"
    MATERIAL_INFORMATION = "material_information"
    PROCESS_DURATION = "process_duration"
    SYSTEM_FAILURE = "system_failure"
    DEPARTMENT_COORDINATION = "department_coordination"
    OTHER = "other"

    @classmethod
    def get_description(cls, ptype):
        descriptions = {
            cls.SERVICE_ATTITUDE: "服务态度",
            cls.MATERIAL_INFORMATION: "材料告知",
            cls.PROCESS_DURATION: "流程时长",
            cls.SYSTEM_FAILURE: "系统故障",
            cls.DEPARTMENT_COORDINATION: "部门协同",
            cls.OTHER: "其他问题"
        }
        return descriptions.get(ptype, "未知类型")


class UrgencyLevel(str, Enum):
    NORMAL = "normal"
    URGENT = "urgent"
    MAJOR = "major"
    SENSITIVE = "sensitive"

    @classmethod
    def get_description(cls, level):
        descriptions = {
            cls.NORMAL: "一般",
            cls.URGENT: "紧急",
            cls.MAJOR: "重大",
            cls.SENSITIVE: "敏感"
        }
        return descriptions.get(level, "未知级别")


class TicketStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    PROCESSING = "processing"
    FEEDBACK = "feedback"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    CLOSED = "closed"
    ESCALATED = "escalated"

    @classmethod
    def get_description(cls, status):
        descriptions = {
            cls.PENDING: "待分派",
            cls.ASSIGNED: "已分派",
            cls.ACCEPTED: "已接单",
            cls.PROCESSING: "处理中",
            cls.FEEDBACK: "待审核",
            cls.REVIEWING: "复核中",
            cls.COMPLETED: "已办结",
            cls.CLOSED: "已关闭",
            cls.ESCALATED: "已升级"
        }
        return descriptions.get(status, "未知状态")


class DepartmentType(str, Enum):
    WINDOW = "window"
    APPROVAL = "approval"
    SUPPORT = "support"
    SUPERVISION = "supervision"

    @classmethod
    def get_description(cls, dtype):
        descriptions = {
            cls.WINDOW: "窗口单位",
            cls.APPROVAL: "审批科室",
            cls.SUPPORT: "后台支撑部门",
            cls.SUPERVISION: "督查部门"
        }
        return descriptions.get(dtype, "未知类型")


class ReminderType(str, Enum):
    ACCEPT_TIMEOUT = "accept_timeout"
    FEEDBACK_TIMEOUT = "feedback_timeout"
    REVIEW_TIMEOUT = "review_timeout"
    ESCALATION = "escalation"

    @classmethod
    def get_description(cls, rtype):
        descriptions = {
            cls.ACCEPT_TIMEOUT: "接单超时催办",
            cls.FEEDBACK_TIMEOUT: "反馈超时催办",
            cls.REVIEW_TIMEOUT: "复核超时催办",
            cls.ESCALATION: "升级报送"
        }
        return descriptions.get(rtype, "未知类型")
