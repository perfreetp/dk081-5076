from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
from datetime import datetime

from app.config.settings import settings
from app.config.database import engine, Base, get_db
try:
    from app.core.scheduler import start_scheduler, stop_scheduler
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    def start_scheduler():
        import logging
        logging.getLogger(__name__).warning("APScheduler未安装，定时任务功能不可用")
    def stop_scheduler():
        pass
from app.api import evaluations, tickets, analysis, archives

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="面向区县营商环境和政务督查条线的好差评闭环督办系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    logger.info(f"请求开始: {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        process_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"请求完成: {request.method} {request.url.path} "
            f"状态码: {response.status_code} 耗时: {process_time:.3f}s"
        )
        return response
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"请求异常: {request.method} {request.url.path} "
            f"异常: {str(e)} 耗时: {process_time:.3f}s",
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"服务器内部错误: {str(e)}",
                "data": None,
                "timestamp": datetime.now().isoformat()
            }
        )


@app.on_event("startup")
async def startup_event():
    logger.info(f"{settings.APP_NAME} 启动中...")
    try:
        start_scheduler()
        logger.info(f"{settings.APP_NAME} 启动成功")
    except Exception as e:
        logger.error(f"启动失败: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"{settings.APP_NAME} 关闭中...")
    try:
        stop_scheduler()
        logger.info(f"{settings.APP_NAME} 关闭成功")
    except Exception as e:
        logger.error(f"关闭失败: {e}", exc_info=True)


@app.get("/", tags=["系统"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "description": "政务好差评闭环督办系统 - 归集、判定、分派、催办、归档"
    }


@app.get("/health", tags=["系统"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


app.include_router(evaluations.router)
app.include_router(tickets.router)
app.include_router(analysis.router)
app.include_router(archives.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG
    )
