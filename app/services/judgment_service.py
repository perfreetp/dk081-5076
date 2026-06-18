from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import Tuple, Optional
import re

from app.core.models import Evaluation
from app.core.enums import (
    ProblemType, UrgencyLevel, EvaluationLevel,
    DataSource
)


class JudgmentService:
    def __init__(self, db: Session):
        self.db = db

    def classify_problem_type(self, content: str) -> str:
        if not content:
            return ProblemType.OTHER

        content = content.lower()

        attitude_keywords = [
            "态度", "语气", "不耐烦", "脸色", "白眼", "训斥", "骂", "冷淡",
            "不理", "不搭理", "推诿", "扯皮", "刁难", "故意", "不给办"
        ]
        if any(keyword in content for keyword in attitude_keywords):
            return ProblemType.SERVICE_ATTITUDE

        material_keywords = [
            "材料", "资料", "证明", "证件", "复印件", "表格", "填写",
            "没说", "没告知", "没说清", "一次不说清", "多次跑", "来回跑",
            "跑多趟", "不一次性告知", "没讲清楚"
        ]
        if any(keyword in content for keyword in material_keywords):
            return ProblemType.MATERIAL_INFORMATION

        duration_keywords = [
            "慢", "等", "排队", "太久", "时间长", "效率低", "太慢",
            "等了半天", "等了好久", "几个小时", "几天", "拖", "拖延",
            "迟迟", "没有动静", "没消息", "进度慢"
        ]
        if any(keyword in content for keyword in duration_keywords):
            return ProblemType.PROCESS_DURATION

        system_keywords = [
            "系统", "网络", "电脑", "打印机", "设备", "坏了", "故障",
            "死机", "卡顿", "登不上", "打不开", "用不了", "不好使",
            "崩溃", "出错", "bug", "技术问题"
        ]
        if any(keyword in content for keyword in system_keywords):
            return ProblemType.SYSTEM_FAILURE

        coordination_keywords = [
            "部门", "科室", "之间", "互相", "踢皮球", "不管", "不属于",
            "找别的", "不归我们", "另外的部门", "协调", "配合", "衔接",
            "多部门", "跨部门"
        ]
        if any(keyword in content for keyword in coordination_keywords):
            return ProblemType.DEPARTMENT_COORDINATION

        return ProblemType.OTHER

    def detect_duplicate(self, evaluation: Evaluation) -> Tuple[bool, Optional[int]]:
        if not evaluation.citizen_phone and not evaluation.citizen_id_card:
            return False, None

        time_window_start = evaluation.evaluate_time - timedelta(hours=72)
        time_window_end = evaluation.evaluate_time + timedelta(hours=24)

        q = self.db.query(Evaluation).filter(
            Evaluation.evaluation_no != evaluation.evaluation_no,
            Evaluation.level.in_([EvaluationLevel.POOR, EvaluationLevel.VERY_POOR]),
            Evaluation.evaluate_time >= time_window_start,
            Evaluation.evaluate_time <= time_window_end,
            Evaluation.is_duplicate == False
        )

        citizen_conditions = []
        if evaluation.citizen_phone:
            citizen_conditions.append(Evaluation.citizen_phone == evaluation.citizen_phone)
        if evaluation.citizen_id_card:
            citizen_conditions.append(Evaluation.citizen_id_card == evaluation.citizen_id_card)
        if citizen_conditions:
            q = q.filter(or_(*citizen_conditions))

        item_conditions = []
        if evaluation.item_code:
            item_conditions.append(Evaluation.item_code == evaluation.item_code)
        if evaluation.item_name:
            item_conditions.append(Evaluation.item_name == evaluation.item_name)
        if item_conditions:
            q = q.filter(or_(*item_conditions))
        else:
            return False, None

        similar = q.first()

        if similar:
            return True, similar.id

        return False, None

    def judge_urgency(self, evaluation: Evaluation) -> str:
        content = (evaluation.content or "").lower()

        sensitive_keywords = [
            "投诉", "举报", "上访", "信访", "媒体", "曝光", "起诉",
            "打官司", "12345", "纪委", "监委", "巡视", "督查", "领导",
            "市长热线", "省长", "市委", "省委", "两会", "节日", "敏感"
        ]

        major_keywords = [
            "聚众", "围堵", "闹事", "冲突", "打人", "受伤", "住院",
            "自杀", "自残", "跳楼", "喝药", "极端", "严重", "恶劣",
            "损失", "赔偿", "巨额", "5000", "1万", "十万", "百万"
        ]

        urgent_keywords = [
            "紧急", "马上", "立刻", "现在", "今天", "当天", "24小时",
            "48小时", "急", "尽快", "特急", "加急", "限期", "超期"
        ]

        if any(keyword in content for keyword in sensitive_keywords):
            return UrgencyLevel.SENSITIVE

        if any(keyword in content for keyword in major_keywords):
            return UrgencyLevel.MAJOR

        if any(keyword in content for keyword in urgent_keywords):
            return UrgencyLevel.URGENT

        if evaluation.level == EvaluationLevel.VERY_POOR:
            return UrgencyLevel.URGENT

        if evaluation.source in [DataSource.HOTLINE_12345, DataSource.SMS]:
            if evaluation.level == EvaluationLevel.POOR:
                return UrgencyLevel.URGENT

        return UrgencyLevel.NORMAL

    def is_major_sensitive(self, evaluation: Evaluation) -> bool:
        urgency = evaluation.urgency_level or self.judge_urgency(evaluation)
        return urgency in [UrgencyLevel.MAJOR, UrgencyLevel.SENSITIVE]

    def calculate_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0

        words1 = set(re.findall(r'[\u4e00-\u9fa5]+', text1))
        words2 = set(re.findall(r'[\u4e00-\u9fa5]+', text2))

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def merge_duplicate_content(self, evaluations):
        contents = []
        suggestions = []
        for eval_item in evaluations:
            if eval_item.content:
                contents.append(f"[{DataSource.get_description(eval_item.source)}] {eval_item.content}")
            if eval_item.suggestion:
                suggestions.append(f"[{DataSource.get_description(eval_item.source)}] {eval_item.suggestion}")

        merged_content = "\n\n".join(contents) if contents else None
        merged_suggestion = "\n\n".join(suggestions) if suggestions else None

        return merged_content, merged_suggestion
