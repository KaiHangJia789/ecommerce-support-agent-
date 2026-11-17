# ACR 与 ECS 交付约定

本阶段只准备可构建的 Linux 镜像与发布工作流，不需要云凭据，不执行云操作。

## 镜像发布

未来推送 GitHub 后，在 `acr-publish` Environment 配置：

| 类别 | 名称 | 内容 |
| --- | --- | --- |
| Variables | ACR_REGISTRY | 当前实例可访问的 registry 主机名，不含协议 |
| Variables | ACR_NAMESPACE | 已创建的命名空间 |
| Secrets | ACR_USERNAME / ACR_PASSWORD | 限定推送权限的登录凭据 |

预先创建 `support-backend` 与 `support-web` 镜像仓库。使用 main 分支的手动 `Publish images to ACR`，构建 linux/amd64、production 目标；输出标签为 `sha-<commit>`，发布清单引用不可变 digest。两个镜像必须都成功并产生清单后才能用于部署，不能以某一个新标签推断整批发布成功。

推荐对该 Environment 配置受保护分支和发布审核。基础 CI 不获得这些 Secrets。ACR 实例类型、地域、访问白名单、认证方式以实际云实例为准，实施 P4 前核对阿里云官方实例文档。

## ECS 基础约定

- 目标为 Linux amd64；变更架构时需要对应构建与测试。
- ECS 仅需运行 Docker/Compose，无需在服务器构建源码；按清单拉取后端与前端。
- 私密 `.env` 放在受限目录；registry 登录凭据由机器侧维护，禁止跟源码或镜像一起分发。
- PostgreSQL/Redis 不暴露公网端口；应用 HTTPS 入口、网络规则和域名在 P4 实施。
- 当前 Compose 的 Nginx 仅绑定回环，不带 TLS；可由后续入口代理访问，但不能把 P0 当作真实多用户客服上线。
- 数据卷需要主机外备份；镜像回滚不能代替数据库回滚。迁移采用兼容策略，每次发布保存前一清单。

## P4 才能开启的部署验收

1. 实现真正的用户登录、对象归属权限、客服审批及模型适配器，并替换 P0 的生产拒绝策略。
2. 配置 HTTPS、运行监控、最小权限、备份及恢复演练。
3. 通过真实实例验证镜像推送/拉取、一次性迁移、健康及业务 smoke。
4. 保存发布清单与兼容的上版清单，演练应用回滚。

因此本次不提供看似能公网部署但缺少完整业务权限的 `deploy.sh`。云部署与回滚脚本在 P4 根据实际 ECS/ACR 环境实现，现阶段依靠镜像、配置边界与清单格式打基础。
