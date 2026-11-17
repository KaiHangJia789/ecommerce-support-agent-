from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from support_agent.domain.models import Run, Ticket
from support_agent.services.tickets import create_ticket

bearer = HTTPBearer(auto_error=False)


def authenticate(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    """功能：以恒定时间比较校验本机共享演示令牌。

    输入：request：携带应用配置的 HTTP 请求；credentials：Bearer 凭据或 None。
    输出：通过时返回 None；缺失或不匹配时抛出 HTTPException(401)。
    """
    expected = request.app.state.settings.demo_api_token.get_secret_value()
    if credentials is None or not compare_digest(
        credentials.credentials.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(401, "unauthorized", headers={"WWW-Authenticate": "Bearer"})


router = APIRouter(prefix="/api/v1", dependencies=[Depends(authenticate)])


class TicketCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    order_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        """功能：拒绝纯空白消息并去除消息首尾空白。

        输入：cls：Pydantic 模型类；value：经过字段类型校验的消息字符串。
        输出：str：去除首尾空白后的消息；纯空白时抛出 ValueError。
        """
        if not value.strip():
            raise ValueError("message cannot be blank")
        return value.strip()


@router.post("/tickets", status_code=202)
def submit_ticket(body: TicketCreate, request: Request):
    """功能：在单一事务中创建工单、执行记录与待投递事件。

    输入：body：已校验的 TicketCreate；request：携带会话工厂的请求。
    输出：dict：ticket_id/run_id，路由返回 HTTP 202；事务失败时整体回滚。
    """
    with request.app.state.factory.begin() as session:
        return create_ticket(session, body.message, body.order_id)


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: UUID, request: Request):
    """功能：查询指定工单的消息、订单、状态和创建时间。

    输入：ticket_id：合法 UUID；request：携带会话工厂的请求。
    输出：dict：工单详情；未找到时抛出 HTTPException(404)。
    """
    with request.app.state.factory() as session:
        ticket = session.get(Ticket, str(ticket_id))
        if ticket is None:
            raise HTTPException(404, "not_found")
        return {
            "ticket_id": ticket.id,
            "message": ticket.message,
            "order_id": ticket.order_id,
            "status": ticket.status,
            "created_at": ticket.created_at,
        }


@router.get("/runs/{run_id}")
def get_run(run_id: UUID, request: Request):
    """功能：查询指定执行记录的状态、结果、错误代码与尝试次数。

    输入：run_id：合法 UUID；request：携带会话工厂的请求。
    输出：dict：执行详情；未找到时抛出 HTTPException(404)。
    """
    with request.app.state.factory() as session:
        run = session.get(Run, str(run_id))
        if run is None:
            raise HTTPException(404, "not_found")
        return {
            "run_id": run.id,
            "ticket_id": run.ticket_id,
            "status": run.status,
            "result": run.result,
            "error_code": run.error_code,
            "attempts": run.attempts,
        }
