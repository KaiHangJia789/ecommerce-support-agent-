from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from support_agent.core.config import Settings
from support_agent.domain.models import OutboxEvent, Run, Ticket
from support_agent.main import create_app


@pytest.fixture
def client(factory):
    """功能：为 API 测试提供使用内存库和假令牌的客户端。

    输入：factory：隔离 SQLite 会话工厂夹具。
    输出：yield TestClient；退出上下文关闭客户端，不连接真实 Redis。
    """
    settings = Settings(
        database_url="sqlite://",
        redis_url="redis://127.0.0.1:1/0",
        demo_api_token="t" * 40,
        app_env="test",
    )
    with TestClient(create_app(settings, factory)) as client:
        yield client


def auth():
    """功能：构造测试用 Bearer 请求头。

    输入：无。
    输出：dict：固定假令牌的 Authorization 头，仅用于测试。
    """
    return {"Authorization": "Bearer " + "t" * 40}


def test_auth_is_required(client):
    """功能：验证工单提交必须携带认证且错误不会泄漏令牌。

    输入：client：测试客户端夹具。
    输出：None；断言未认证请求返回 401 且响应不含令牌。
    """
    response = client.post("/api/v1/tickets", json={"message": "where is my order"})
    assert response.status_code == 401
    assert "t" * 40 not in response.text


def test_malformed_bearer_returns_401(client):
    """功能：验证错误 Bearer 值返回未认证。

    输入：client：测试客户端夹具。
    输出：None；断言接口返回 HTTP 401。
    """
    response = client.get(
        "/api/v1/runs/" + str(uuid4()), headers={"Authorization": "Bearer " + "wrong-token"}
    )
    assert response.status_code == 401


def test_non_ascii_bearer_returns_401(client):
    """功能：验证非 ASCII 凭据返回 401 而不会触发内部错误。

    输入：client：测试客户端夹具；请求使用非 ASCII 假凭据字节。
    输出：None；断言接口返回 HTTP 401。
    """
    response = client.get(
        "/api/v1/runs/" + str(uuid4()), headers={b"Authorization": b"Bearer \xff"}
    )
    assert response.status_code == 401


def test_unexpected_database_error_is_sanitized(client, monkeypatch):
    """功能：验证数据库异常的敏感消息不会返回客户端。

    输入：client：测试客户端；monkeypatch：pytest 属性替换夹具。
    输出：None；断言 HTTP 500 和通用错误码，响应不含模拟私密消息。
    """

    def broken_factory():
        """功能：模拟携带敏感错误消息的数据库创建故障。

        输入：无。
        输出：不正常返回；抛出 RuntimeError 供脱敏回归测试捕获。
        """
        raise RuntimeError("private_database_password_should_never_appear")

    monkeypatch.setattr(client.app.state, "factory", broken_factory)
    response = client.get("/api/v1/runs/" + str(uuid4()), headers=auth())
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "private_database_password_should_never_appear" not in response.text


def test_create_and_query_with_atomic_outbox(client, factory):
    """功能：验证工单可创建和查询，且工单、执行、事件同时入库。

    输入：client：测试客户端；factory：内存会话工厂。
    输出：None；断言 HTTP 202、查询字段与各表记录数量。
    """
    response = client.post(
        "/api/v1/tickets",
        headers=auth(),
        json={"message": "物流一直没有更新", "order_id": "DEMO-1001"},
    )
    assert response.status_code == 202
    data = response.json()
    assert client.get(f"/api/v1/runs/{data['run_id']}", headers=auth()).json()["status"] == "queued"
    assert (
        client.get(f"/api/v1/tickets/{data['ticket_id']}", headers=auth()).json()["order_id"]
        == "DEMO-1001"
    )
    with factory() as session:
        for model in (Ticket, Run, OutboxEvent):
            assert session.scalar(select(func.count()).select_from(model)) == 1


@pytest.mark.parametrize("message", ["", "   ", "x" * 4001])
def test_invalid_input_creates_nothing(client, factory, message):
    """功能：验证空白或超长输入被拒绝且不创建工单。

    输入：client/factory：测试夹具；message：参数化的无效消息。
    输出：None；断言 HTTP 422、长消息不回显且数据库未写入。
    """
    response = client.post("/api/v1/tickets", headers=auth(), json={"message": message})
    assert response.status_code == 422
    assert message not in response.text if len(message) > 100 else True
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Ticket)) == 0


def test_invalid_and_missing_ids(client):
    """功能：验证错误 UUID 与不存在的执行 ID 使用正确错误响应。

    输入：client：测试客户端。
    输出：None；断言 HTTP 422/404 及 not_found 错误码。
    """
    assert client.get("/api/v1/runs/not-a-uuid", headers=auth()).status_code == 422
    response = client.get(f"/api/v1/runs/{uuid4()}", headers=auth())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_health_and_request_id(client):
    """功能：验证存活接口、请求 ID 清洗与依赖失败响应。

    输入：client：Redis 不可用的测试客户端。
    输出：None；断言 Mock 存活、非法请求 ID 被替换及 ready 返回 503。
    """
    live = client.get("/health/live", headers={"X-Request-ID": "untrusted\tvalue"})
    assert live.status_code == 200
    assert live.json()["mode"] == "mock"
    assert live.headers["x-request-id"] != "untrusted\tvalue"
    assert client.get("/health/ready").status_code == 503
