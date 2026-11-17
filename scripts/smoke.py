"""Exercise the running demo without printing tokens (stdlib only)."""

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from bootstrap import read_config


def request(base: str, token: str, path: str, payload=None):
    """功能：向演示 API 发送带令牌的 JSON 请求。

    输入：base：服务地址；token：本机令牌；path：接口路径；payload：可选 JSON 请求体。
    输出：解析后的 JSON；有 payload 时使用 POST，否则 GET；HTTP/网络错误向上抛出。
    """
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        base + path,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


def main():
    """功能：验证存活、就绪及工单从入库到 Worker 成功回复的完整链路。

    输入：命令行 --base-url/--timeout；隐式读取项目根目录 .env 的端口与演示令牌。
    输出：None；成功打印执行 ID，失败抛出异常；会创建一条合成演示工单，不输出令牌。
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    values = read_config(Path(__file__).resolve().parents[1] / ".env")
    base = args.base_url or f"http://127.0.0.1:{values.get('HTTP_PORT', '18080')}"
    token = values["DEMO_API_TOKEN"]
    live = request(base, token, "/health/live")
    assert live["mode"] == "mock", "Expected mock mode"
    assert request(base, token, "/health/ready")["status"] == "ready"
    ids = request(
        base,
        token,
        "/api/v1/tickets",
        {"message": "我的物流一直没有更新，请查询", "order_id": "DEMO-1001"},
    )
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        run = request(base, token, f"/api/v1/runs/{ids['run_id']}")
        if run["status"] == "failed":
            raise RuntimeError(f"Worker failed: {run['error_code']}")
        if run["status"] == "succeeded":
            assert run["result"]["mode"] == "mock"
            assert run["result"]["intent"] == "logistics"
            assert run["attempts"] == 1
            assert (
                request(base, token, f"/api/v1/tickets/{ids['ticket_id']}")["status"] == "resolved"
            )
            print(
                f"PASS: API -> outbox -> Redis -> Worker -> graph checkpoint -> DB ({ids['run_id']})"
            )
            return
        time.sleep(1)
    raise TimeoutError("Task still queued; inspect worker health and outbox")


if __name__ == "__main__":
    try:
        main()
    except (
        urllib.error.URLError,
        TimeoutError,
        RuntimeError,
        AssertionError,
        KeyError,
    ) as error:
        raise SystemExit(
            f"Smoke failed ({type(error).__name__}); check services and configuration"
        ) from None
