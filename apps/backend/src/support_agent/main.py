import logging
import re
from contextlib import asynccontextmanager
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from support_agent.api.routes import router
from support_agent.core.config import Settings, get_settings
from support_agent.core.logging import configure_logging
from support_agent.repositories.database import create_factory

logger = logging.getLogger("support_agent")


def create_app(settings: Settings | None = None, factory=None) -> FastAPI:
    """功能：创建 API、依赖容器、中间件、异常处理器与健康检查路由。

    输入：settings：可选配置，缺省读取环境；factory：可选注入会话工厂。
    输出：FastAPI 实例；仅关闭本函数自行创建的数据库连接池。
    """
    settings = settings or get_settings()
    owned_factory = factory is None
    factory = factory or create_factory(settings)

    @asynccontextmanager
    async def lifespan(app):
        """功能：在应用启动时配置日志，关闭时释放自有数据库连接池。

        输入：app：当前 FastAPI 实例；闭包读取 factory 和 owned_factory。
        输出：异步上下文管理器，yield 后进入服务阶段；退出时执行连接池清理。
        """
        configure_logging()
        yield
        if owned_factory:
            factory.kw["bind"].dispose()

    app = FastAPI(
        title="E-commerce support — P0 Mock",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.factory = factory

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        """功能：分配安全请求 ID，捕获未处理异常并记录不含正文的请求结果。

        输入：request：HTTP 请求；call_next：下游请求处理函数。
        输出：Response：带 X-Request-ID/Cache-Control；未知错误返回脱敏 HTTP 500。
        """
        supplied = request.headers.get("x-request-id", "")
        request.state.request_id = (
            supplied if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", supplied) else str(uuid4())
        )
        start = monotonic()
        try:
            response = await call_next(request)
        except Exception as error:
            # Never emit exception messages: drivers can include URLs or user data.
            logger.error(
                "request_failed",
                extra={"request_id": request.state.request_id, "error_type": type(error).__name__},
            )
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {"code": "internal_error", "request_id": request.state.request_id}
                },
            )
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        logger.info(
            "request_completed",
            extra={
                "request_id": request.state.request_id,
                "status": response.status_code,
                "elapsed_ms": round((monotonic() - start) * 1000),
            },
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        """功能：将已知 HTTP 异常转换为统一错误结构。

        输入：request：含 request_id 的请求；error：HTTPException。
        输出：JSONResponse：保留状态码及必要头，仅返回错误代码与请求 ID。
        """
        code = error.detail if isinstance(error.detail, str) else "request_error"
        return JSONResponse(
            status_code=error.status_code,
            headers=error.headers,
            content={"error": {"code": code, "request_id": request.state.request_id}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        """功能：将输入校验异常转换为不回显原始输入的错误响应。

        输入：request：含 request_id 的请求；error：RequestValidationError。
        输出：JSONResponse：HTTP 422，包含字段路径、validation_error 及请求 ID。
        """
        fields = [".".join(str(part) for part in item["loc"]) for item in error.errors()]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "fields": fields,
                    "request_id": request.state.request_id,
                }
            },
        )

    @app.get("/health/live")
    def live():
        """功能：报告 API 进程存活与当前 Mock 版本。

        输入：无。
        输出：dict：status=ok、mode=mock、version；不检查数据库或 Worker。
        """
        return {"status": "ok", "mode": "mock", "version": "0.1.0"}

    def dependencies_ready():
        """功能：检查数据库与 Redis 是否可用。

        输入：无显式参数；闭包读取会话工厂及 Redis 配置。
        输出：None；成功完成 SELECT 1/PING，不可用时抛出异常并释放连接。
        """
        with factory() as session:
            session.execute(text("SELECT 1"))
        with Redis.from_url(
            settings.redis_url.get_secret_value(), socket_connect_timeout=1, socket_timeout=1
        ) as redis:
            redis.ping()

    @app.get("/health/ready")
    async def ready():
        """功能：在线程池检查 API 的数据库与 Redis 依赖，避免阻塞事件循环。

        输入：无显式参数；调用闭包中的 dependencies_ready。
        输出：成功返回 ready 字典；失败返回 HTTP 503 JSONResponse，不暴露异常内容。
        """
        try:
            await run_in_threadpool(dependencies_ready)
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return {"status": "ready"}

    app.include_router(router)
    return app
