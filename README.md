# 政务好差评闭环督办系统

面向区县营商环境和政务督查条线的后端服务，专门承接来自政务大厅、政务App、12345、评价器和短信回访的好差评数据，把分散线索汇成统一督办闭环。

## 系统能力

系统提供5类核心能力：

1. **归集** - 统一接收多来源评价和回访结果
2. **判定** - 识别重复差评、区分问题类型、判定紧急程度
3. **分派** - 根据事项归属自动分派到责任部门
4. **催办** - 对超时事项自动催办、升级报送
5. **归档** - 保留完整流转轨迹、生成统一办结说明

## 核心功能

- 统一接收5类来源数据：政务大厅、政务App、12345热线、评价器、短信回访
- 智能识别同一群众、同一事项、同一时段的重复差评并合并处置
- 按问题性质自动分类：服务态度、材料告知、流程时长、系统故障、部门协同
- 根据事项归属自动分派到窗口单位、审批科室或后台支撑部门
- 对超时未接单、未反馈、未复核事项自动催办
- 对重大敏感差评自动升级报送
- 保留完整流转轨迹，便于问责和复盘
- 向前端系统输出整改状态、回访结论和办结口径
- 生成跨渠道一致的办结说明，减少群众多头重复解释
- 沉淀地区高频差评画像，为制度优化提供依据

## 技术栈

- **框架**: FastAPI 0.109.0
- **数据库**: SQLite (默认) / PostgreSQL
- **ORM**: SQLAlchemy 2.0.25
- **数据校验**: Pydantic 2.5.3
- **定时任务**: APScheduler 3.10.4
- **异步服务**: Uvicorn

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python init_db.py
```

### 3. 插入测试数据（可选）

```bash
python test_data.py
```

### 4. 启动服务

```bash
python main.py
```

服务启动后访问:
- API文档: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

## API接口

### 评价归集 (`/api/evaluations`)

- `POST /receive` - 接收单条评价数据
- `POST /receive/batch` - 批量接收评价数据
- `GET /{evaluation_id}` - 查询评价详情
- `GET /no/{evaluation_no}` - 按单号查询
- `GET` - 分页查询评价列表
- `GET /{evaluation_id}/duplicates` - 查询重复评价

### 工单管理 (`/api/tickets`)

- `GET /{ticket_id}` - 查询工单详情
- `GET /no/{ticket_no}` - 按单号查询
- `GET /status/{ticket_no}` - 查询工单处理状态
- `GET` - 分页查询工单列表
- `POST /assign` - 人工分派工单
- `POST /accept` - 接单
- `POST /reject` - 拒收
- `POST /process` - 更新处理进度
- `POST /feedback` - 提交处理结果
- `POST /review` - 复核
- `POST /complete` - 办结归档
- `POST /{ticket_id}/remind` - 人工催办
- `POST /{ticket_id}/escalate` - 升级报送
- `GET /{ticket_id}/trail` - 查询流转轨迹
- `GET /{ticket_id}/reminders` - 查询催办记录
- `GET /{ticket_id}/evaluations` - 查询关联评价
- `GET /{ticket_id}/archive` - 查询归档记录
- `POST /{ticket_id}/reopen` - 重新打开工单
- `POST /{ticket_id}/close` - 关闭工单

### 统计分析 (`/api/analysis`)

- `GET /overview` - 总览统计
- `GET /problem-types` - 问题类型统计
- `GET /departments` - 部门统计
- `GET /time-series` - 时间序列趋势
- `GET /high-frequency` - 高频问题画像
- `GET /source-distribution` - 来源分布
- `GET /closing-statement/{ticket_no}` - 获取办结说明

### 归档管理 (`/api/archives`)

- `GET` - 分页查询归档记录
- `GET /{archive_id}` - 查询归档详情
- `GET /no/{archive_no}` - 按归档号查询
- `GET /ticket/{ticket_id}` - 按工单查询
- `GET /{archive_id}/snapshot` - 获取归档快照
- `POST /auto-archive` - 执行自动归档

## 定时任务

系统启动后自动运行以下定时任务：

1. **超时催办检查** - 每小时执行一次，检查超时工单并自动催办
2. **自动归档** - 每日凌晨2:00执行，自动归档办结30天以上的工单
3. **每日超时统计** - 每日早上8:30执行，统计超时工单

## 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── config/              # 配置模块
│   │   ├── __init__.py
│   │   ├── settings.py      # 系统配置
│   │   └── database.py      # 数据库连接
│   ├── core/                # 核心模块
│   │   ├── __init__.py
│   │   ├── enums.py         # 枚举定义
│   │   ├── models.py        # 数据模型
│   │   └── scheduler.py     # 定时任务
│   ├── schemas/             # 数据传输对象
│   │   ├── __init__.py
│   │   ├── common.py        # 通用响应
│   │   ├── evaluation.py    # 评价相关
│   │   └── ticket.py        # 工单相关
│   ├── services/            # 业务服务
│   │   ├── __init__.py
│   │   ├── collection_service.py   # 归集服务
│   │   ├── judgment_service.py     # 判定服务
│   │   ├── dispatch_service.py     # 分派服务
│   │   ├── reminder_service.py     # 催办服务
│   │   ├── archive_service.py      # 归档服务
│   │   ├── ticket_service.py       # 工单服务
│   │   ├── analysis_service.py     # 分析服务
│   │   └── trail_service.py        # 轨迹服务
│   └── api/                 # API接口
│       ├── __init__.py
│       ├── evaluations.py   # 评价接口
│       ├── tickets.py       # 工单接口
│       ├── analysis.py      # 分析接口
│       └── archives.py      # 归档接口
├── main.py                  # 应用入口
├── init_db.py               # 数据库初始化
├── test_data.py             # 测试数据生成
├── requirements.txt         # 依赖列表
├── .env.example             # 环境变量示例
├── .gitignore
└── README.md
```

## 数据模型

### 核心数据表

1. **evaluations** - 评价表：存储各渠道的评价数据
2. **tickets** - 工单表：督办工单主表
3. **assignments** - 分派表：工单分派记录
4. **reminders** - 催办表：催办和升级记录
5. **operation_logs** - 操作日志表：完整流转轨迹
6. **archives** - 归档表：办结工单归档快照
7. **departments** - 部门表：责任部门配置
8. **item_mappings** - 事项映射表：事项与责任部门映射

## 问题类型分类

系统支持6类问题自动识别：

| 类型 | 描述 |
|------|------|
| SERVICE_ATTITUDE | 服务态度问题 |
| MATERIAL_INFORMATION | 材料告知问题 |
| PROCESS_DURATION | 流程时长问题 |
| SYSTEM_FAILURE | 系统故障问题 |
| DEPARTMENT_COORDINATION | 部门协同问题 |
| OTHER | 其他问题 |

## 紧急程度分级

| 级别 | 描述 | 响应时限 |
|------|------|----------|
| NORMAL | 一般 | 72小时 |
| URGENT | 紧急 | 24小时 |
| MAJOR | 重大 | 12小时 |
| SENSITIVE | 敏感 | 6小时 |

## 配置说明

复制 `.env.example` 为 `.env` 并修改相关配置：

```bash
cp .env.example .env
```

主要配置项：

- `DB_*` - 数据库连接配置
- `SUPERVISE_TIMEOUT_HOURS` - 接单超时时间（小时）
- `FEEDBACK_TIMEOUT_HOURS` - 反馈超时时间（小时）
- `REVIEW_TIMEOUT_HOURS` - 复核超时时间（小时）
- `URGENT_UPGRADE_HOURS` - 紧急工单升级时限
- `MAJOR_UPGRADE_HOURS` - 重大工单升级时限

## 系统特色

1. **多源数据归一化** - 统一5类来源数据格式，形成完整闭环
2. **智能判定引擎** - 关键词匹配+规则引擎，自动分类和去重
3. **自动分派机制** - 事项映射+问题类型+部门类型，精准分派
4. **多级催办体系** - 超时自动催办、升级报送、人工干预
5. **全链路可追溯** - 每一步操作留痕，完整轨迹可查
6. **跨渠道一致性** - 统一办结说明，多渠道答复口径一致
7. **数据驱动决策** - 高频问题画像、趋势分析、部门排名
