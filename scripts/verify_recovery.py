"""Check queued-work recovery and data persistence in this local Compose demo only."""

import subprocess
import time
from pathlib import Path

from bootstrap import read_config
from smoke import request

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "-f", "compose.yaml", "-f", "compose.dev.yaml"]


def compose(*args):
    """功能：对当前项目执行指定 Docker Compose 操作。

    输入：*args：Compose 子命令及参数；ROOT/COMPOSE：当前项目路径与基础命令。
    输出：None；操作本项目容器并捕获命令输出，失败抛出 CalledProcessError。
    """
    subprocess.run([*COMPOSE, *args], cwd=ROOT, check=True, capture_output=True)


def wait_for(check, timeout=90):
    """功能：在超时前轮询条件，允许服务恢复期间的短暂异常。

    输入：check：无参数条件函数；timeout：最大等待秒数，默认 90。
    输出：条件为真时返回 None；超时抛出 TimeoutError。
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutError("Local demo recovery timed out")


def main():
    """功能：验证 Worker 停机期间的工单恢复及服务重启后的结果持久化。

    输入：隐式读取本地 .env；要求当前项目为 development 且 API 已启动。
    输出：None；成功打印验证结果；短暂停止/重启当前项目服务，最终尝试恢复服务。
    """
    values = read_config(ROOT / ".env")
    assert values.get("APP_ENV") == "development", "Local development only"
    base = f"http://127.0.0.1:{values.get('HTTP_PORT', '18080')}"
    token = values["DEMO_API_TOKEN"]
    assert request(base, token, "/health/live")["mode"] == "mock"
    try:
        compose("stop", "worker")
        ids = request(
            base,
            token,
            "/api/v1/tickets",
            {"message": "查询物流", "order_id": "DEMO-1001"},
        )
        path = f"/api/v1/runs/{ids['run_id']}"
        assert request(base, token, path)["status"] == "queued"
        compose("start", "worker")
        # 功能：检测执行成功；输入：无（闭包读取 base/token/path）；输出：bool。
        wait_for(lambda: request(base, token, path)["status"] == "succeeded")
        original = request(base, token, path)["result"]
        compose("restart", "postgres", "redis", "worker")
        # 功能：检测 API 依赖恢复；输入：无（闭包配置）；输出：bool，ready 时为 True。
        wait_for(lambda: request(base, token, "/health/ready").get("status") == "ready")
        # 功能：检测原执行状态；输入：无（闭包配置）；输出：bool，succeeded 时为 True。
        wait_for(lambda: request(base, token, path)["status"] == "succeeded")
        restored = request(base, token, path)
        assert restored["result"] == original
        assert restored["attempts"] == 1
        print(
            "PASS: worker-off submission recovered; result persisted across DB/Redis/worker restart"
        )
    finally:
        compose("start", "postgres", "redis", "worker")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(
            f"Recovery check failed ({type(error).__name__}); inspect local services"
        ) from None
