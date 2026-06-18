from app.config.database import engine, Base, SessionLocal
from app.core.models import Department, ItemMapping
from app.core.enums import DepartmentType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    logger.info("开始初始化数据库...")

    Base.metadata.drop_all(bind=engine)
    logger.info("已删除旧表")

    Base.metadata.create_all(bind=engine)
    logger.info("已创建新表")

    db = SessionLocal()

    try:
        departments = [
            Department(
                dept_code="SUP001",
                dept_name="营商环境督查室",
                dept_type=DepartmentType.SUPERVISION,
                parent_code=None,
                level=1,
                sort_order=1,
                contact_person="张主任",
                contact_phone="13800000001",
                supervisor="李局长",
                supervisor_phone="13900000001",
                item_codes=["*"]
            ),
            Department(
                dept_code="WIN001",
                dept_name="政务服务大厅综合窗口",
                dept_type=DepartmentType.WINDOW,
                parent_code=None,
                level=1,
                sort_order=2,
                contact_person="王班长",
                contact_phone="13800000002",
                supervisor="刘主任",
                supervisor_phone="13900000002",
                item_codes=["001", "002", "003", "004"]
            ),
            Department(
                dept_code="WIN002",
                dept_name="不动产登记窗口",
                dept_type=DepartmentType.WINDOW,
                parent_code=None,
                level=1,
                sort_order=3,
                contact_person="赵班长",
                contact_phone="13800000003",
                supervisor="陈主任",
                supervisor_phone="13900000003",
                item_codes=["101", "102", "103"]
            ),
            Department(
                dept_code="WIN003",
                dept_name="市场监管窗口",
                dept_type=DepartmentType.WINDOW,
                parent_code=None,
                level=1,
                sort_order=4,
                contact_person="孙班长",
                contact_phone="13800000004",
                supervisor="周主任",
                supervisor_phone="13900000004",
                item_codes=["201", "202", "203"]
            ),
            Department(
                dept_code="WIN004",
                dept_name="税务服务窗口",
                dept_type=DepartmentType.WINDOW,
                parent_code=None,
                level=1,
                sort_order=5,
                contact_person="吴班长",
                contact_phone="13800000005",
                supervisor="郑主任",
                supervisor_phone="13900000005",
                item_codes=["301", "302", "303"]
            ),
            Department(
                dept_code="APP001",
                dept_name="审批一科",
                dept_type=DepartmentType.APPROVAL,
                parent_code=None,
                level=1,
                sort_order=6,
                contact_person="冯科长",
                contact_phone="13800000006",
                supervisor="陈局长",
                supervisor_phone="13900000006",
                item_codes=["101", "102", "103"]
            ),
            Department(
                dept_code="APP002",
                dept_name="审批二科",
                dept_type=DepartmentType.APPROVAL,
                parent_code=None,
                level=1,
                sort_order=7,
                contact_person="褚科长",
                contact_phone="13800000007",
                supervisor="卫局长",
                supervisor_phone="13900000007",
                item_codes=["201", "202", "203"]
            ),
            Department(
                dept_code="SUP002",
                dept_name="信息技术科",
                dept_type=DepartmentType.SUPPORT,
                parent_code=None,
                level=1,
                sort_order=8,
                contact_person="蒋科长",
                contact_phone="13800000008",
                supervisor="沈主任",
                supervisor_phone="13900000008",
                item_codes=["SYS001", "SYS002"]
            ),
            Department(
                dept_code="SUP003",
                dept_name="后勤保障科",
                dept_type=DepartmentType.SUPPORT,
                parent_code=None,
                level=1,
                sort_order=9,
                contact_person="韩科长",
                contact_phone="13800000009",
                supervisor="杨主任",
                supervisor_phone="13900000009",
                item_codes=["LOG001", "LOG002"]
            )
        ]

        for dept in departments:
            existing = db.query(Department).filter(Department.dept_code == dept.dept_code).first()
            if not existing:
                db.add(dept)
                logger.info(f"添加部门: {dept.dept_code} - {dept.dept_name}")

        db.commit()

        item_mappings = [
            ItemMapping(
                item_code="001",
                item_name="身份证办理",
                item_category="户籍证件",
                primary_dept_code="WIN001",
                primary_dept_name="政务服务大厅综合窗口",
                primary_dept_type=DepartmentType.WINDOW,
                support_dept_codes=["SUP002"],
                approval_dept_codes=["APP001"],
                keywords=["身份证", "补办", "换证", "办理"],
                problem_keywords=["态度", "慢", "材料"]
            ),
            ItemMapping(
                item_code="101",
                item_name="不动产登记",
                item_category="不动产",
                primary_dept_code="WIN002",
                primary_dept_name="不动产登记窗口",
                primary_dept_type=DepartmentType.WINDOW,
                support_dept_codes=["SUP002", "SUP003"],
                approval_dept_codes=["APP001"],
                keywords=["不动产", "房产证", "登记", "过户"],
                problem_keywords=["材料", "流程", "协同"]
            ),
            ItemMapping(
                item_code="201",
                item_name="营业执照办理",
                item_category="市场监管",
                primary_dept_code="WIN003",
                primary_dept_name="市场监管窗口",
                primary_dept_type=DepartmentType.WINDOW,
                support_dept_codes=["SUP002"],
                approval_dept_codes=["APP002"],
                keywords=["营业执照", "工商", "注册", "注销", "变更"],
                problem_keywords=["材料", "系统", "态度"]
            ),
            ItemMapping(
                item_code="301",
                item_name="纳税申报",
                item_category="税务",
                primary_dept_code="WIN004",
                primary_dept_name="税务服务窗口",
                primary_dept_type=DepartmentType.WINDOW,
                support_dept_codes=["SUP002"],
                approval_dept_codes=["APP002"],
                keywords=["纳税", "申报", "税务", "发票"],
                problem_keywords=["系统", "流程", "态度"]
            ),
            ItemMapping(
                item_code="SYS001",
                item_name="政务服务系统",
                item_category="系统支撑",
                primary_dept_code="SUP002",
                primary_dept_name="信息技术科",
                primary_dept_type=DepartmentType.SUPPORT,
                support_dept_codes=[],
                approval_dept_codes=[],
                keywords=["系统", "网络", "登录", "卡顿", "崩溃"],
                problem_keywords=["系统", "故障", "技术"]
            )
        ]

        for mapping in item_mappings:
            existing = db.query(ItemMapping).filter(ItemMapping.item_code == mapping.item_code).first()
            if not existing:
                db.add(mapping)
                logger.info(f"添加事项映射: {mapping.item_code} - {mapping.item_name}")

        db.commit()
        logger.info("数据库初始化完成")

    except Exception as e:
        logger.error(f"初始化失败: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
