# 本地开发与验证

所有命令从仓库根目录执行。公开页面只访问回环地址；P0 仅测试合成数据。

## 工具与平台

- Windows：Docker Desktop Linux containers；PowerShell、Python 3.10+。
- Linux：Docker Engine、Compose 插件、Python 3.10+。
- macOS：Docker Desktop、Python 3.10+。macOS 启动入口按标准 shell 编写，是否实测见验证记录。
- 宿主调试需要 Python 3.12/uv、Node.js 24/pnpm；纯 Docker 运行不需要这些宿主依赖。

优先执行 README 快速启动。若 uv 检测到本机注册表中已删除的 Python 路径，使用 `uv python install 3.12` 后以 `--python-preference only-managed` 执行项目命令，避免修改系统 Python。

Windows 一键运行：根目录 `start.cmd`；无交互运行：`start.cmd --no-pause`。该入口通过脚本自身路径定位仓库，支持中文/空格路径及从其他目录调用，依次执行 setup、dev 和 smoke。脚本仅临时绕过当前 PowerShell 进程策略，不修改系统执行策略。需要 Docker Desktop 已启动并选择 Linux containers，服务与容器开发环境的部署方式不变。

宿主 Python 开发环境：双击 `setup-env.cmd`，用后端锁文件在根目录生成 `.venv`（Python 3.12）。同步时临时设置 `UV_PROJECT_ENVIRONMENT`，退出后恢复之前的值。Windows 检查使用 `scripts/check.ps1`；Linux/macOS 首次同步使用 `UV_PROJECT_ENVIRONMENT="$PWD/.venv" uv sync --project apps/backend --frozen`，检查使用 `sh scripts/check.sh`。直接手动执行 `uv run --project apps/backend` 时也需要设置这一变量，否则 uv 默认仍选择 `apps/backend/.venv`。

根 `.venv` 供宿主工具使用，不能通过它直接访问 Compose 内的 `postgres`/`redis` 主机名；完整服务请用 `start.cmd`。已有后端 `.venv` 不删除。若复制或移动目录，重新运行 `setup-env.cmd` 重建，勿把虚拟环境复制给其他用户。

## 容器测试

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec -T api python -m pytest -m "not integration"
```

PostgreSQL 集成测试使用单独的 `support_test` 数据库；测试不删除已有数据库或表。以下方式在已启动容器内创建缺失测试库、设置临时环境并初始化，不把密码输出到终端：

```sh
docker compose -f compose.yaml -f compose.dev.yaml exec -T api python -m support_agent.verify_postgres
```

该命令仅接受 `APP_ENV=development/test`，以当前已初始化角色创建固定名称 `support_test`，不会连接外部客户数据库。验证并发重复投递、持久化检查点及过期事件重新投递。真实队列端到端测试使用 `python scripts/smoke.py`。

## 重启恢复验证

```sh
python scripts/verify_recovery.py
```

验证脚本仅停止、重启当前目录 Compose 项目的 Worker/PostgreSQL/Redis 服务，并通过 `finally` 恢复服务；无需删除容器或数据卷。先在 Worker 暂停时提交工单，确认 queued，再启动 Worker 等待成功；随后重启数据服务与 Worker，确认原结果仍存在。

该脚本会短暂中断本演示，不能在共用的生产系统使用。恢复后 API 的短暂依赖故障通过健康检查观察；业务状态不靠 Redis 保存。

## 常见问题

| 现象 | 排查 |
| --- | --- |
| Docker API 管道不可达 | 启动 Docker Desktop，确认 Linux containers，运行 `docker info` |
| 首次构建超时 | 检查 Docker Hub、PyPI、npm 网络；重试构建，不删除数据卷 |
| 端口占用 | 修改 `.env` 的 HTTP_PORT，重新启动 |
| 401 | 从本机 `.env` 检查 DEMO_API_TOKEN；不是填写模型密钥 |
| 长时间 queued | 查看 Worker 健康、日志与 Redis；恢复 Worker 后事件会周期重投 |
| 503 ready | 检查 PostgreSQL/Redis 健康和迁移服务退出状态 |
| 修改数据库密码后连接失败 | 数据卷保留原有密码；不能仅更改 `.env` 来更新数据库角色密码 |
| 修改 Worker 代码未生效 | 开发 Worker 需要手动 restart，只有 API/Web 热更新 |
| Docker Desktop 未检测到文件改动 | 源码已经挂载；若宿主文件事件未透传，restart 对应 api/web 服务 |

## 生产布局的本地验证

先构建 `production` 目标并使用不同镜像标签：

```sh
docker build --target production -t ecommerce-support-backend:p0 apps/backend
docker build --target production -t ecommerce-support-web:p0 apps/web
```

从开发布局切换前先 `down`，保留卷；在本机 `.env` 追加 `BACKEND_IMAGE=ecommerce-support-backend:p0`、`WEB_IMAGE=ecommerce-support-web:p0` 后：

```sh
docker compose -f compose.yaml -f compose.prod.yaml up -d --wait --wait-timeout 180
python scripts/smoke.py
```

保持 `APP_ENV=development`，只验证镜像形态。P0 不能用 `APP_ENV=production` 启动。结束后 `down`，移除本机额外镜像变量，再恢复开发布局。
