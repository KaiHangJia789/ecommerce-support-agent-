# 电商售后多 Agent 工单系统

面向电商售后的多模态、多 Agent 系统。当前交付 **P0 工程基础**：本地 Docker、工单 API、事务 outbox、Celery Worker、LangGraph 持久化与演示页面。

**现在能体验：**提交合成订单问题，轮询任务状态，查看确定性规则分类与模拟物流回复。已预留退款、退货、破损的分类；这些类型仅提示等待后续处理。

**当前边界：**没有调用真实模型/物流，没有执行退款，没有图片理解、真实用户登录或人工审批恢复。页面中的“待人工处理”仅为状态标识。请只提交合成数据；本版本仅适合本机演示，拒绝 `APP_ENV=production`。

## 快速启动

支持 `git clone` 或 GitHub **Code → Download ZIP**；ZIP 解压后进入含 `compose.yaml` 的目录即可，不依赖 `.git`。

前提：Docker Engine / Docker Desktop **Linux containers**（Docker Engine 24+、Compose v2.24+）、宿主机 Python 3.10+（只负责标准库初始化与 smoke）。首次启动需要访问 Docker Hub、PyPI、npm 下载镜像和依赖。日常运行的 Python/Node 在容器中，无需宿主安装 uv、pnpm、PostgreSQL 或 Redis。

Windows 也可以直接双击根目录 **`start.cmd`**，自动初始化私密配置、构建/启动 Docker 服务并验证工单处理链路。首次运行先启动 Docker Desktop；下载 ZIP 后同样可用。窗口会保留运行结果；命令行自动调用使用 `start.cmd --no-pause`，失败返回非零退出码。关闭窗口不会停止容器。

Windows PowerShell：

```powershell
./scripts/setup.ps1
./scripts/dev.ps1
python scripts/smoke.py
```

如果 PowerShell 策略限制脚本，可用不修改系统策略的等价命令：

```powershell
python scripts/bootstrap.py
docker compose -f compose.yaml -f compose.dev.yaml up --build -d --wait --wait-timeout 240
python scripts/smoke.py
```

Linux / macOS：

```sh
sh scripts/setup.sh
sh scripts/dev.sh
python3 scripts/smoke.py
```

打开 **http://127.0.0.1:18080**。默认只绑定回环地址，数据库与 Redis 不发布宿主端口。端口占用时，修改本机 `.env` 中的 `HTTP_PORT` 后重新启动。

本机编辑器打开初始化生成的 `.env`，把 `DEMO_API_TOKEN` 的值填到页面“本机演示令牌”。该令牌不是模型密钥，只保存在当前页面内存。示例订单：`DEMO-1001`（运输延迟）、`DEMO-1002`（已签收）。工单回复完成后不会自动关闭。

初始化只创建缺失的 `.env`，每份配置生成独立随机凭据和 `COMPOSE_PROJECT_NAME`，隔离各下载目录的容器、数据卷和本地镜像；再次执行保留原文件。多份安装同时运行时，还需分别设置 `HTTP_PORT`。配置不合法会明确报错，请在本机修正对应字段。`.env.example` 只含公开模板。不要把真实客户、图片、密钥填入演示消息。

## 常用操作

```sh
# 状态与日志
docker compose -f compose.yaml -f compose.dev.yaml ps
docker compose -f compose.yaml -f compose.dev.yaml logs --tail 60 api worker

# 停止容器并保留数据库与队列卷；重新启动沿用快速启动命令
docker compose -f compose.yaml -f compose.dev.yaml down

# 修改 Worker 代码后重启；API 与 Web 在开发模式下支持热更新
docker compose -f compose.yaml -f compose.dev.yaml restart worker
```

首次构建时间由网络决定。失败后可重新运行启动命令，查看具体构建步骤。不要在普通排错时使用 `down -v`，它会删除本项目的数据卷。

## 结构与执行流程

```text
浏览器 → Nginx → Next.js / FastAPI
                      ↓
             PostgreSQL 工单 + outbox（同一事务）
                      ↓
             Worker 内置 Beat 定期投递 → Redis
                      ↓
             Celery → LangGraph → PostgreSQL 检查点与结果
```

任务采用至少一次投递；30 秒后未完成的 outbox 事件可重发。PostgreSQL 行锁和终态检查防止同次执行重复写结果。P0 的单 Worker 容器包含一个 Beat，暂不支持直接横向复制 Worker。规则节点没有外部副作用；接入真实售后工具前需补充动作幂等与权限。

```text
apps/backend/      FastAPI、业务模型、迁移、LangGraph、任务与测试
apps/web/          Next.js 演示页面
scripts/           初始化、检查、smoke、敏感信息扫描
infra/nginx/       同源路由
docs/              设计、实施计划、依赖基线与运行手册
.github/workflows/ CI 与手动 ACR 镜像发布
```

业务路由需要 `Authorization: Bearer <本机演示令牌>`：

| 接口 | 用途 |
| --- | --- |
| `POST /api/v1/tickets` | `{ "message": "查询物流", "order_id": "DEMO-1001" }`，返回工单与执行 ID |
| `GET /api/v1/tickets/{ticket_id}` | 查看工单状态 |
| `GET /api/v1/runs/{run_id}` | 查看执行状态与结果 |
| `GET /health/live` | 进程存活与 Mock 标识 |
| `GET /health/ready` | API 的数据库/Redis 依赖是否可用；不代表 Worker 就绪 |

P0 的单演示令牌没有客户间权限隔离，禁止据此作为公网客服。每次失败返回可追踪的 request_id，响应和应用日志不回显请求体、令牌或数据库连接串。

## 开发与检查

宿主开发工具：uv 0.12.23、Python 3.12、Node.js 24、pnpm 11.25.0。容器路径不依赖开发者机器。

**Python 环境分工：**根目录 `.venv` 是宿主开发/检查环境（Python 3.12），依赖仍由 `apps/backend/pyproject.toml` 和 `uv.lock` 统一锁定；Docker 内 `/app/.venv` 是实际 API/Worker 的独立运行环境。原有 `apps/backend/.venv` 可以保留，但本地检查脚本已统一使用根环境。Node 依赖由 pnpm 管理，不安装进 Python 虚拟环境。

Windows 双击 **`setup-env.cmd`** 创建/同步根环境（需先安装 uv）；也可执行：

```powershell
.\setup-env.cmd --no-pause
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
.\scripts\check.ps1
```

CMD 激活方式为 `call .venv\Scripts\activate.bat`。若 PowerShell 不允许激活，直接调用 `.venv\Scripts\python.exe` 即可。编辑器请选择此解释器。`.venv` 不上传、不随 ZIP 分发，其他用户下载后自行重建。运行 Docker 演示可直接用 `start.cmd`，无需先安装全部宿主开发工具。

```sh
uv python install 3.12
UV_PROJECT_ENVIRONMENT="$PWD/.venv" uv sync --project apps/backend --frozen --python-preference only-managed
pnpm --dir apps/web install --frozen-lockfile
# Windows: ./scripts/check.ps1
sh scripts/check.sh
pnpm --dir apps/web build
```

数据库迁移和检查点初始化由 `migrate` 一次性服务负责，成功后 API/Worker 才启动。运行 PostgreSQL 集成测试及重启验证的方法见 [本地验证手册](docs/runbooks/local-development.md)。

所有自有 Python 函数在函数体开头用中文 docstring 说明“功能、输入、输出”，前端函数使用对应的 JSDoc；匿名回调在相邻位置标注。生成代码与第三方依赖不修改。后续新增函数沿用此约定。

版本记录见 [依赖基线](docs/dependency-baseline.md)，实测范围见 [P0 验证记录](docs/runbooks/verification-2026-11-17.md) 与 [本地环境/启动入口验证](docs/runbooks/verification-local-environment-2026-11-17.md)。

## GitHub、ACR 与 ECS

- CI 在无云账号、无模型密钥的情况下检查测试和 Linux 镜像。
- `publish-images.yml` 为 `main` 分支手动发布入口，使用 `acr-publish` GitHub Environment；分别发布 backend/web 镜像并保存同一提交的 digest 清单。
- ACR 可保持私有。下载源码的用户通过本地 Docker 构建运行，无需获得作者的 ACR 凭据。
- `compose.prod.yaml` 提供无源码挂载的镜像布局与资源限制。当前只能以明确的本地 Mock 配置验证，仍绑定回环地址；不是已完成的公网生产部署。
- ECS 的 HTTPS、完整鉴权、备份恢复与实际发布/回滚属于后续 P4。当前尚未创建云资源或连接 ECS。

详情见 [云交付约定](docs/runbooks/acr-ecs.md)。

## 公开仓库与配置

真实 `.env`、云凭据、SSH/TLS 私钥、运行数据、日志和备份均被排除。镜像按明确的源码路径复制文件，并另有 `.dockerignore`。只公开合成演示数据。

提交前检查忽略规则和暂存文件，并运行：

```sh
python scripts/scan_secrets.py --staged
# GitHub release 下载不可达时，用固定 digest 的官方容器（需先拉取镜像）
docker pull ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f
python scripts/scan_secrets.py --docker --staged
# 已有提交后，检查历史
python scripts/scan_secrets.py
```

扫描器从官方 GitHub release 下载固定版本 Gitleaks 并核对校验和，输出强制脱敏。扫描不能代替人工核对；凭据若曾泄漏，需先吊销或轮换。

**许可待项目所有者确定。** 当前未擅自添加开源 LICENSE；正式公开分发前需选择许可证，补齐第三方数据/图片的来源与授权。本仓库现有演示订单为代码生成，无外部业务数据。
