# P0 工程与环境基础 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从公开源码启动独立的本地电商售后演示，验证 API → 数据库/outbox → Redis → Worker/LangGraph → 持久化结果。

**Architecture:** 单仓库；后端同一镜像启动 API 和 Worker；Next.js 页面通过 Nginx 同源调用。Mock 逻辑无外部模型调用，数据库与图检查点持久化，配置在本机生成。

**Tech Stack:** Python 3.12、uv、FastAPI、SQLAlchemy/Alembic、PostgreSQL/pgvector、Redis/Celery、LangGraph、Next.js/TypeScript、Docker Compose。

**Spec:** `docs/superpowers/specs/2026-11-14-ecommerce-support-design.md`

## Global Constraints

- 最终仓库公开；配置示例不含真实凭据；clone/ZIP 启动不依赖私有 ACR 或开发者机器。
- 单商家、合成数据、Mock 模型；P0 不实现真实退款、图片理解或完整身份系统。
- api 与 worker 共用 backend 镜像；云端发布使用 digest 固定版本。
- 外部账户与密钥不作为 P0 先决条件；生产环境配置不接受演示回退。
- 初始化配置幂等；本地服务入口仅绑定回环；不改变已有容器和数据。

## Review Focus

- 用户反复初始化：保留已有配置，损坏配置明确报错而非静默覆盖（Task 1）。
- 空白/超长输入、无效 UUID、错误令牌：返回受控错误且不回显凭据（Task 2）。
- Redis 暂时故障或进程重启：已保存请求可重新投递，无重复结果（Task 3）。
- ZIP 无 .git、含空格/中文路径：脚本可定位根目录，依赖不含宿主路径（Task 4/5）。
- 生产配置缺项或默认 Mock：启动失败，避免误作真实售后服务（Task 1/5）。

### Task 1: 仓库、配置与工具链

**Files:** `.gitignore`, `.gitattributes`, `.env.example`, `scripts/bootstrap.py`, `scripts/setup.ps1`, `scripts/setup.sh`, `apps/backend/pyproject.toml`, `.python-version`, `apps/backend/tests/test_settings.py`, `tests/test_bootstrap.py`。

**Interfaces:** `bootstrap.initialize(root: Path) -> bool`；`Settings` 从环境读取 `APP_ENV`、`DATABASE_URL`、`REDIS_URL`、`DEMO_API_TOKEN`、`MODEL_PROVIDER`。

- [x] 写配置生成、保留已有文件、占位值拒绝、生产 Mock 拒绝测试；观察缺失实现失败。
- [x] 实现仅生成本地文件的初始化和严格配置，安装锁定依赖。
- [x] 测试通过；Git 初始化在 `feat/p0-foundation`，检查实际环境文件被忽略。

### Task 2: API 与业务数据

**Files:** `apps/backend/src/support_agent/{main.py,core/,domain/,services/,repositories/,api/}`, `apps/backend/migrations/`, `apps/backend/tests/test_api.py`。

**Interfaces:** `POST /api/v1/tickets -> {ticket_id,run_id}`；`GET /api/v1/tickets/{uuid}`；`GET /api/v1/runs/{uuid}`；`/health/live`、`/health/ready`；业务路由需要演示 bearer token。

- [x] 用临时数据库验证认证、校验、创建原子性、查询、404 与错误脱敏，先运行失败。
- [x] 实现工单、执行、outbox 和合成订单模型；Alembic 初始迁移；JSON 日志与 request_id。
- [x] 执行 API 单元测试和静态检查。

### Task 3: 后台任务与持久化图

**Files:** `worker.py`, `tasks/`, `agents/`, `scripts/smoke.py`, `apps/backend/tests/test_workflow.py`, `apps/backend/tests/integration/test_postgres.py`。

**Interfaces:** `execute_run(run_id: str, factory, checkpointer) -> None`；`dispatch_pending` 至少一次投递；独立命令 `python -m support_agent.initialize` 执行 Alembic 与 checkpointer setup。

- [x] 写成功、重复执行、缺订单、图检查点和 Broker 故障后重发测试，运行失败。
- [x] 实现显式 Mock 的确定性 LangGraph，按 run 行锁串行化同次执行；outbox 保留至执行成功，周期重投。
- [x] 本地数据库测试通过，后续在真实 PostgreSQL/Redis 跑集成及重启 smoke。

### Task 4: 前端与容器

**Files:** `apps/web/`, 两个 Dockerfile, `compose*.yaml`, `infra/nginx/`, `scripts/dev.*`, `scripts/check.*`。

**Interfaces:** 页面不内置令牌，使用者在本机输入演示令牌；同源 `/api`；支持提交与轮询；仅前端必要交互为客户端组件。

- [x] 用现成 smoke 契约验证实际容器；配置合并检查先确认缺失文件失败。
- [x] 实现简洁中文演示页面、开发热更新和生产 standalone 镜像；数据库迁移一次性执行后启动应用。
- [x] 本地验证 Compose、两种镜像、网页与 smoke；停止 Worker 后建单再启动，验证恢复。

### Task 5: 公开交付、CI 与云发布接口

**Files:** `README.md`, `docs/runbooks/`, `.github/workflows/`, `scripts/release.py`, `scripts/deploy.sh`, `scripts/rollback.sh`, `docs/dependency-baseline.md`。

**Interfaces:** CI 无私密变量；手动 ACR 发布输出两种镜像 digest 的发布清单；部署前置检查拒绝 P0 演示公开上线。

- [x] 文档提供 PowerShell/shell、Mock 限制、数据保留、排错和后续云步骤；整理个人路径。
- [x] 检查依赖锁定、忽略规则和敏感信息；从干净源码 ZIP 验证启动；运行 CI 等价检查。
- [x] 独立最终代码审查；修复重要问题，记录实测证据与尚未进行的云端操作。

## Execution rulings

- 用户已明确要求“实施”，继续本会话执行，不再次请求计划许可。
- 初始目录只有设计文档且没有 Git，因此直接初始化专用分支，无需复制或新建 worktree；无已有实现可基线测试。
- 不擅自选择公开许可证：在 README 明确代码发布前需确定 LICENSE；避免假定用户授予某个许可证。
- P0 只交付模拟文本与持久化图基础；真实模型、图片、审批完整功能属于 P1-P3，不作为已完成功能展示。
- Task 5 原列出的 release/deploy/rollback 脚本推迟至 P4；本次以手动镜像发布工作流、digest 清单和云交付手册落实接口，避免将本地演示误作公网服务。
- 本地完成 CI 中的应用测试、Linux 镜像与 smoke 对应检查；未创建远端仓库，因此 GitHub 实际执行与提交历史扫描未发生。详见 `docs/runbooks/verification-2026-11-17.md`。
