# P0 验证记录

日期：2026-11-17。范围：Windows 宿主、Docker Desktop Linux containers、linux/amd64；仅合成数据和 Mock 工作流。

## 结果

| 项目 | 实测结果 |
| --- | --- |
| 初始化脚本 | 3 项 unittest 通过；随机生成、再次执行保留文件、非法配置拒绝；不同目录生成独立 Compose 项目名 |
| 后端单元测试 | Windows 与 Linux 容器均为 18 项通过 |
| PostgreSQL 集成 | 独立 support_test 数据库中 2 项通过，验证并发重复消费、检查点重连持久化和事件过期重投 |
| 静态检查 | 后端 Ruff lint/format、前端 TypeScript 通过 |
| 开发环境 | PostgreSQL、Redis、API、Worker、Web、Nginx 健康；迁移服务成功退出 |
| 端到端 | 主环境、ZIP 独立环境、production 目标镜像布局均通过工单 smoke |
| 故障恢复 | Worker 停机建单后恢复执行；PostgreSQL/Redis/Worker 重启后结果和单次执行次数保留 |
| 浏览器 | Chromium 实际提交并收到模拟回复；1440px/390px 无横向溢出，刷新清除令牌；无页面或控制台错误 |
| Linux 镜像 | backend/web 的 development 与 production 目标构建通过；最终后端镜像不含 pytest、Ruff、测试目录、builder 缓存或 .env |
| 镜像配置 | 最终 backend/web 使用非 root 用户；镜像配置中不含本机生成的令牌和数据库密码 |
| 下载 ZIP | 从暂存源码文件集合打包，排除 .git/.env；在含中文和空格的路径执行 setup/dev/smoke 通过；更新源码后再次构建成功且私密配置保留 |
| 多份安装隔离 | ZIP 使用独立项目、数据卷、镜像及端口；原项目容器 ID 未改变 |
| 构建上下文 | backend/web 中放置嵌套 .env、私钥、secrets/uploads 合成哨兵文件，实际 Docker COPY 检查确认全部排除；随后移除哨兵文件 |
| 源码扫描 | Gitleaks 8.30.1 官方固定 digest 容器扫描暂存内容，无泄漏发现；当前没有提交历史 |
| Shell 入口 | Linux 容器内 sh -n 通过，标准库 bootstrap 生成及幂等检查通过 |
| CI 文件 | YAML 解析通过，Action 引用固定 40 位提交 SHA；GitHub 执行尚未发生 |
| 独立审查 | 已修复安装项目名冲突、Docker 私密文件排除、Nginx DNS 更新、非 ASCII 令牌及成功重试遗留错误码；复核无重要遗留项 |

## 验证命令

```powershell
./scripts/check.ps1
docker compose -f compose.yaml -f compose.dev.yaml exec -T api python -m pytest -m "not integration"
docker compose -f compose.yaml -f compose.dev.yaml exec -T api python -m support_agent.verify_postgres
python scripts/smoke.py
python scripts/verify_recovery.py
docker build --target production -t ecommerce-support-backend:p0 apps/backend
docker build --target production -t ecommerce-support-web:p0 apps/web
python scripts/scan_secrets.py --staged --docker
git diff --cached --check
```

宿主检查会跳过 2 项没有 TEST_DATABASE_URL 的集成测试；这 2 项另在真实 PostgreSQL 上通过，不将跳过算作通过。

## 发现并修复

- 固定 Compose 全局名称会让第二份下载目录共用旧容器与数据卷：改为每份 .env 持久化随机项目名，并用于本地镜像标签。
- Docker 上下文原先遗漏嵌套私密目录：改为源码白名单与递归排除；前端采用明确 COPY 路径。
- Nginx 静态上游解析可能保留旧地址：使用 Docker DNS 和可重新解析的 upstream；重建 API/Web 后同源入口恢复可用。
- 非 ASCII Bearer 比较原先触发 500：改为字节比较，返回 401；失败后重试成功清除旧 error_code。对应测试先失败、修复后通过。
- Chrome 的 HTML pattern 使用 v 标志时要求转义字符类中的连字符：浏览器复现后修复订单输入规则。
- Next.js 开发服务器拒绝回环来源的热更新连接：明确允许 localhost/127.0.0.1。
- PyPI 下载存在超时：限制并发并增加超时；共享 builder，离线整理生产依赖；最终镜像仅复制生产虚拟环境。
- GitHub release 二进制下载在当前网络不可达：增加固定 digest 官方容器扫描入口。原生下载失败仍明确返回失败，不跳过扫描。

## 实测边界

没有提交或推送 Git，没有创建 GitHub 远程仓库；因此没有将实际 clone 和远端 GitHub Actions 运行列为实测通过。ZIP 已验证无 .git 启动；clone 使用同一套入口。

没有登录 ACR、发布远程镜像、连接 ECS 或创建云资源。production 是镜像构建目标，本次仍为 APP_ENV=development 的回环 Mock 测试，不能据此宣称已生产上线。

没有实测 macOS、ARM64 或独立 Linux 宿主上的完整启动。Linux 应用、构建及 shell 检查是在 Docker Desktop 的 Linux 容器完成。

真实模型、图片处理、RAG、人工审批恢复、真实用户权限、退款执行及云端备份恢复仍属于后续阶段。公开许可证待所有者确定。
