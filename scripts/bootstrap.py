"""Create private demo configuration without overwriting an existing file (stdlib only)."""

import os
import re
import secrets
from pathlib import Path


def read_config(path: Path) -> dict[str, str]:
    """功能：读取本机配置并拒绝重复键，不展开环境变量。

    输入：path：UTF-8 配置文件路径。
    输出：dict[str, str]：配置键值；重复键抛出 ValueError，读取失败抛出 OSError。
    """
    result = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if key in result:
                raise ValueError(f"Duplicate configuration key: {key}")
            result[key] = value
    return result


def validate_config(path: Path) -> None:
    """功能：校验演示配置的项目名、凭据格式、运行模式与端口。

    输入：path：待验证配置路径；只在本机读取配置。
    输出：None；不修改文件，配置无效时抛出 ValueError，错误不包含凭据值。
    """
    values = read_config(path)
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,62}", values.get("COMPOSE_PROJECT_NAME", "")):
        raise ValueError("COMPOSE_PROJECT_NAME requires 3-63 lowercase URL-safe characters")
    for key in ("POSTGRES_PASSWORD", "DEMO_API_TOKEN"):
        # URL-safe generated values work in dotenv, Compose interpolation and DB URLs.
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,}", values.get(key, "")):
            raise ValueError(f"{key}: requires at least 32 URL-safe characters; file preserved")
    if values.get("APP_ENV") != "development" or values.get("MODEL_PROVIDER") != "mock":
        raise ValueError("P0 setup requires APP_ENV=development and MODEL_PROVIDER=mock")
    try:
        port = int(values.get("HTTP_PORT", "18080"))
        if not 1024 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise ValueError("HTTP_PORT must be between 1024 and 65535") from None


def initialize(root: Path) -> bool:
    """功能：仅在配置缺失时生成随机演示凭据，并校验最终配置。

    输入：root：含 .env.example 的项目根目录。
    输出：bool：新建返回 True，已有合法配置返回 False；不覆盖已有文件，失败抛出异常。
    """
    target = root / ".env"
    if target.exists():
        validate_config(target)
        return False
    template = (root / ".env.example").read_text(encoding="utf-8")
    template = template.replace(
        "COMPOSE_PROJECT_NAME=\n",
        f"COMPOSE_PROJECT_NAME=support-{secrets.token_hex(6)}\n",
    )
    for name in ("POSTGRES_PASSWORD", "DEMO_API_TOKEN"):
        template = template.replace(f"{name}=\n", f"{name}={secrets.token_urlsafe(36)}\n")
    # Exclusive creation protects an existing configuration, even on concurrent setup.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
        output.write(template)
    validate_config(target)
    return True


if __name__ == "__main__":
    try:
        created = initialize(Path(__file__).resolve().parents[1])
    except (ValueError, OSError) as error:
        # No file contents or credential values are printed.
        raise SystemExit(str(error)) from None
    print("Created private .env" if created else "Existing .env validated and preserved")
