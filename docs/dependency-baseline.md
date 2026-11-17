# 依赖基线

记录日期：2026-11-17。以仓库内锁文件和 Dockerfile 为可执行依据；这里是关键依赖摘要，不代表持续跟踪的最新版。

## 应用依赖

| 组件 | 锁定版本 | 来源 |
| --- | --- | --- |
| Python | 3.12.15（容器） | backend Dockerfile |
| uv | 0.12.23 | backend Dockerfile / CI |
| FastAPI | 0.163.1 | uv.lock |
| SQLAlchemy | 2.1.9 | uv.lock |
| Alembic | 1.20.1 | uv.lock |
| psycopg | 3.3.9 | uv.lock |
| Celery | 5.7.0 | uv.lock |
| Redis Python client | 8.1.0 | uv.lock |
| LangGraph | 1.2.22 | uv.lock |
| LangGraph PostgreSQL checkpointer | 3.2.1 | uv.lock |
| Pydantic Settings | 2.16.3 | uv.lock |
| Uvicorn | 0.54.0 | uv.lock |
| pytest / Ruff | 9.2.0 / 0.17.5 | uv.lock |
| Node.js | 24.18.0（容器） | web Dockerfile |
| pnpm | 11.25.0 | package.json / web Dockerfile |
| Next.js | 16.4.6 | package.json / pnpm-lock.yaml |
| React / React DOM | 19.3.1 | package.json / pnpm-lock.yaml |
| Gitleaks | 8.30.1 | scripts/scan_secrets.py |

应用依赖分别使用 `uv sync --frozen` 与 `pnpm install --frozen-lockfile`。uv.lock 保存依赖分发文件哈希，pnpm-lock.yaml 保存包完整性信息。P0 不要求模型密钥。

## 容器基线

Dockerfile 和 Compose 同时固定标签与 digest；升级时修改这些文件并重新执行构建、迁移、smoke 和恢复检查。

| 用途 | 镜像标签 | digest |
| --- | --- | --- |
| 后端 | python:3.12.15-slim | `sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704` |
| 前端 | node:24.18.0-alpine | `sha256:a0b9bf06e4e6193cf7a0f58816cc935ff8c2a908f81e6f1a95432d679c54fbfd` |
| uv | ghcr.io/astral-sh/uv:0.12.23 | `sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21` |
| PostgreSQL | pgvector/pgvector:pg17 | `sha256:b513c48566e4777cd3370451400000c78eda6a08131d68f4c31d4a76f27bd8fd` |
| Redis | redis:7.4-alpine | `sha256:7f7d30b7fdd09467bac58198a1f166dd69789d348d4fe859cccb20e0cf287fbe` |
| Nginx | nginx:1.28-alpine | `sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236` |
| 源码扫描 | ghcr.io/gitleaks/gitleaks:v8.30.1 | `sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f` |

后端 builder 安装构建和开发依赖，再离线整理生产虚拟环境；最终 production 阶段仅复制该虚拟环境、应用源码及迁移文件，不复制 builder 缓存或测试目录。前端最终阶段复制 Next.js standalone 输出。私密配置只在运行容器时注入，不作为构建参数。

## 维护约定

- 升级依赖时先更新锁文件，再验证；不要在 CI 或启动脚本中临时解除版本锁定。
- GitHub Actions 固定提交 SHA；工作流中的版本注释用于识别维护目标。
- 当前 ACR 工作流仅构建 `linux/amd64`，与计划中的 ECS 架构保持一致；ARM/macOS 未完成实机验证。
- Langfuse、模型 SDK、图片处理和 RAG 的依赖留待对应阶段按实际接入需求添加。
