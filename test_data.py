from datetime import datetime, timedelta
import random
import string

from app.config.database import SessionLocal
from app.core.enums import DataSource, EvaluationLevel
from app.schemas.evaluation import EvaluationCreate
from app.services.collection_service import CollectionService

def generate_random_id(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_phone():
    return '138' + ''.join(random.choices(string.digits, k=8))

def generate_name():
    surnames = ['张', '王', '李', '赵', '刘', '陈', '杨', '黄', '周', '吴']
    names = ['伟', '芳', '娜', '敏', '静', '强', '磊', '军', '洋', '勇']
    return random.choice(surnames) + random.choice(names)

citizens = [
    {"name": generate_name(), "phone": generate_phone(), "id_card": f"110101{random.randint(1970, 2000):04d}{random.randint(1,12):02d}{random.randint(1,28):02d}{random.randint(1000,9999):04d}"}
    for _ in range(20)
]

items = [
    {"code": "001", "name": "身份证办理", "category": "户籍证件", "dept_code": "WIN001", "dept_name": "政务服务大厅综合窗口"},
    {"code": "101", "name": "不动产登记", "category": "不动产", "dept_code": "WIN002", "dept_name": "不动产登记窗口"},
    {"code": "201", "name": "营业执照办理", "category": "市场监管", "dept_code": "WIN003", "dept_name": "市场监管窗口"},
    {"code": "301", "name": "纳税申报", "category": "税务", "dept_code": "WIN004", "dept_name": "税务服务窗口"},
]

negative_contents = [
    "工作人员态度很差，问问题不耐烦，还翻白眼。",
    "材料没说清楚，让我跑了三趟才办完事。",
    "排队等了两个小时，效率太低了！",
    "系统一直登录不上，浪费我一上午时间。",
    "部门之间互相推诿，都说不归自己管。",
    "办理时间太长，说好5个工作日，结果等了半个月。",
    "一次性告知不到位，每次去都要补材料。",
    "工作人员语气生硬，服务态度恶劣。",
    "打印机坏了也不修，让我自己出去打印。",
    "网上预约了还是要排队，系统形同虚设。",
    "窗口人员业务不熟练，半天办不完一个业务。",
    "咨询电话永远打不通，太不负责任了。"
]

positive_contents = [
    "服务态度很好，讲解很耐心，点赞！",
    "办事效率很高，很快就办完了。",
    "工作人员很热情，主动帮我解决问题。",
    "网上办事很方便，不用跑大厅了。",
    "一次就办好了，非常满意。"
]

def generate_evaluation_data(source: DataSource, is_negative: bool, citizen_index: int = None):
    if citizen_index is None:
        citizen = random.choice(citizens)
    else:
        citizen = citizens[citizen_index % len(citizens)]

    item = random.choice(items)

    if is_negative:
        level = random.choice([EvaluationLevel.POOR, EvaluationLevel.VERY_POOR])
        score = random.randint(1, 3)
        content = random.choice(negative_contents)
    else:
        level = random.choice([EvaluationLevel.GOOD, EvaluationLevel.EXCELLENT])
        score = random.randint(4, 5)
        content = random.choice(positive_contents)

    days_ago = random.randint(0, 30)
    evaluate_time = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
    happen_time = evaluate_time - timedelta(hours=random.randint(1, 72))

    return EvaluationCreate(
        evaluation_no=f"EVAL{generate_random_id()}",
        source=source,
        level=level,
        score=score,
        citizen_id=f"CID{generate_random_id()}",
        citizen_name=citizen["name"],
        citizen_phone=citizen["phone"],
        citizen_id_card=citizen["id_card"],
        item_code=item["code"],
        item_name=item["name"],
        item_category=item["category"],
        dept_code=item["dept_code"],
        dept_name=item["dept_name"],
        window_no=f"W{random.randint(1, 10):02d}",
        handler_name=generate_name(),
        content=content,
        suggestion="希望能够改进服务质量。",
        happen_time=happen_time,
        evaluate_time=evaluate_time
    )

def insert_test_data():
    db = SessionLocal()
    service = CollectionService(db)

    print("开始插入测试数据...")

    total_count = 0

    for source in [DataSource.HALL, DataSource.APP, DataSource.HOTLINE_12345, DataSource.EVALUATOR, DataSource.SMS]:
        for i in range(8):
            is_negative = i < 5
            eval_data = generate_evaluation_data(source, is_negative)
            service.receive_evaluation(eval_data, operator="test")
            total_count += 1
            print(f"插入 {DataSource.get_description(source)} 数据: {'差评' if is_negative else '好评'} - {eval_data.evaluation_no}")

    same_citizen = citizens[0]
    same_item = items[0]
    base_time = datetime.now() - timedelta(hours=24)

    for i, source in enumerate([DataSource.HALL, DataSource.APP, DataSource.HOTLINE_12345]):
        eval_data = EvaluationCreate(
            evaluation_no=f"EVALDUP{generate_random_id()}",
            source=source,
            level=EvaluationLevel.POOR,
            score=2,
            citizen_id=f"CID{generate_random_id()}",
            citizen_name=same_citizen["name"],
            citizen_phone=same_citizen["phone"],
            citizen_id_card=same_citizen["id_card"],
            item_code=same_item["code"],
            item_name=same_item["name"],
            item_category=same_item["category"],
            dept_code=same_item["dept_code"],
            dept_name=same_item["dept_name"],
            window_no="W03",
            handler_name=generate_name(),
            content="工作人员态度很差，问了几次都不耐烦，让我回去等消息。",
            suggestion="希望加强工作人员培训。",
            happen_time=base_time - timedelta(hours=1),
            evaluate_time=base_time + timedelta(hours=i * 2)
        )
        service.receive_evaluation(eval_data, operator="test")
        total_count += 1
        print(f"插入重复差评测试数据: {DataSource.get_description(source)} - {eval_data.evaluation_no}")

    print(f"\n测试数据插入完成，共插入 {total_count} 条评价记录")
    print("系统已自动识别重复差评并创建工单")

    db.close()

if __name__ == "__main__":
    insert_test_data()
