# 本地环境与启动入口验证（2026-11-17）

## 交付

- 根目录 `.venv`：uv 创建的 CPython 3.12.15 环境，76 个后端及开发依赖按原锁文件同步，不使用系统 Anaconda。原 `apps/backend/.venv` 保留。
- `setup-env.cmd`：创建/同步根环境；重复执行检查现有依赖，不覆盖 `.env`，退出恢复 `UV_PROJECT_ENVIRONMENT`。
- `start.cmd`：setup → Docker Compose 开发栈 → smoke → 输出本机地址。默认 pause，`--no-pause` 供命令行验证；失败退出码非零。
- 74 个自有 Python 函数含嵌套函数、夹具、测试及迁移，均有中文功能/输入/输出 docstring。前端 12 个函数及回调具有对应说明；代码生成产物与第三方依赖不修改。

## 已验证

- 根环境实际路径及 Python 版本；重复同步成功；临时环境变量恢复，私密配置字节不变。
- Python 函数文档完整性及对应准确性扫描通过；剔除 docstring 后的全部 Python 可执行 AST 与改动前一致。
- 前端移除注释后生成的 JavaScript 与改动前逐字一致。
- `scripts/check.ps1`：标准库测试 3 项、后端单元测试 18 项通过；Ruff lint/format 与 TypeScript 检查通过。宿主因未配置测试库跳过 2 项集成测试；这两项随后在 API 容器的独立 PostgreSQL 测试库实际运行通过。
- Windows `start.cmd --no-pause` 实际构建/启动成功，完整 API → outbox → Redis → Worker → 图检查点 → 数据库链路通过，退出码 0。
- 源文件 ZIP 不含 `.git`、`.env` 或 `.venv`，提取至中文/空格目录后实际调用 `start.cmd --no-pause` 成功，在独立项目/18081 端口验证完整工单链路；已有私密配置保持不变。验证后停止临时项目容器，保留其数据卷，主项目继续运行。
- 通过假的 Docker 命令模拟服务不可用和 Windows containers 模式，两种情况均及时退出非零，未改写私密配置；从含空格的其他目录调用成功定位项目。
- PowerShell 脚本语法解析通过；Linux 容器中各 `.sh` 的 `sh -n` 通过。只读脚本审查未发现重要问题。
- `.env`、根/后端 `.venv` 和本机编辑器配置被 Git 忽略；公开源文件集合不包含实际本机令牌或数据库密码。构建上下文继续使用原有显式目录及排除规则。

启动仍使用本机 Docker，宿主虚拟环境用于编辑器和开发检查。此次未验证新的 GitHub 远程运行、ACR/ECS 发布或 macOS；不涉及真实模型、退款或客户数据。
