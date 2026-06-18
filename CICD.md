# CI/CD 部署指南

项目：Virtual Pal（Vue + FastAPI + Redis + Docker）

---

## 一、方案概览

```
你 git push 到 develop
    ↓
CI 触发（.github/workflows/ci.yml）
  ├── backend: lint → test → docker build
  ├── frontend: type-check → build → docker build
  └── integration: docker compose up → curl 验证
    ↓
你提 PR: develop → main，code review 通过后合并
    ↓
合并到 main → CI 再次触发（通过后）
    ↓
CD 自动触发（.github/workflows/cd.yml）
  ├── docker build（打 commit SHA 标签）
  ├── docker save → gzip 打包
  ├── SCP 到服务器 /opt/virtual-pal/
  ├── docker load → tag latest → compose up -d
  └── curl http://82.156.15.50/api/v1/health ✔
```

**设计思路：** 不走 Docker Hub（国内拉取慢），而是直接在 GitHub Actions 上构建镜像，打包成 tar.gz，通过 SCP 传送到服务器，`docker load` 加载后启动。用 commit SHA 做版本标签，支持回滚。

---

## 二、准备工作

### 2.1 GitHub Secrets

路径：GitHub 仓库 → **Settings → Secrets and variables → Actions**

| Secret 名称 | 值 |
|---|---|
| `SERVER_HOST` | `82.156.15.50` |
| `SERVER_SSH_KEY` | 服务器的 SSH 私钥 |

#### 如何获取 SERVER_SSH_KEY

```bash
# 在你本地开发机上（不是服务器）
# 生成密钥对（如果没有的话）
ssh-keygen -t ed25519 -f ~/.ssh/virtual-pal-deploy

# 把公钥添加到服务器
ssh-copy-id -i ~/.ssh/virtual-pal-deploy.pub root@82.156.15.50

# 把私钥内容复制出来，黏贴到 GitHub Secrets
cat ~/.ssh/virtual-pal-deploy
```

> Windows 用户可以用 `type %USERPROFILE%\.ssh\virtual-pal-deploy` 查看私钥内容，复制全部（包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 到 `-----END OPENSSH PRIVATE KEY-----`）。

### 2.2 服务器确认

```bash
# SSH 登录服务器
ssh root@82.156.15.50

# 确认 Docker 已安装
docker --version
docker compose version
```

> 如果服务器没装 Docker：参考 https://docs.docker.com/engine/install/

### 2.3 服务器上创建部署目录

```bash
# 在服务器上执行
mkdir -p /opt/virtual-pal
```

> 这个目录只需要建一次，后续 CD 会自动文件覆盖。

---

## 三、CI 流水线

CI 配置文件：`.github/workflows/ci.yml`

### 触发条件

- `develop` 或 `main` 分支有 push 时
- `main` 分支有 PR 时

### 三个 Job

| Job | 内容 |
|---|---|
| `backend` | Ruff lint → pytest → docker build |
| `frontend` | Type check → npm build → docker build |
| `integration` | docker compose up → curl health 端点验证 |

所有 Job 都通过后，CI 为绿色，CD 才能触发。

---

## 四、CD 流水线

CD 配置文件：`.github/workflows/cd.yml`

### 触发条件

CI 在 `main` 分支上跑过且结果为 `success`。

### 步骤详解

1. **Build** — 用 commit SHA 打标签构建前后端镜像
2. **Package** — `docker save` + `gzip` 打包为 tar.gz，一并打包部署版 `docker-compose.yml`
3. **SCP** — 通过 `appleboy/scp-action` 将所有文件传送到服务器 `/opt/virtual-pal/`
4. **Deploy** — SSH 到服务器执行：
   - `docker load` 加载新镜像
   - 标记为 `latest`（docker compose 引用这个标签）
   - `docker compose up -d` 重启服务
   - 清理旧版本，只保留最近 3 个 SHA 标签
5. **Health check** — curl 验证服务正常

### 镜像版本管理

- 每次部署用 commit SHA 打标签（如 `virtual-pal-backend:a1b2c3d`）
- 同时标记为 `latest` 供 docker compose 引用
- 服务器保留最近 3 个 SHA 版本，超出自动清理

---

## 五、首次部署

### 5.1 本地确认

```bash
# 确认项目能本地构建
cd backend && docker build -t virtual-pal-backend .
cd ../frontend && docker build -t virtual-pal-frontend .
```

### 5.2 推送到 main

```bash
git checkout main
git merge develop
git push origin main
```

### 5.3 观察流水线

1. GitHub 仓库 → **Actions** 标签页
2. 先看到 CI 在跑（lint → test → build → integration）
3. CI 通过后，CD 自动触发
4. CD 完成后访问 http://82.156.15.50 和 http://82.156.15.50:8000/api/v1/health

---

## 六、回滚

如果新版本部署后出问题：

```bash
# 登录服务器
ssh root@82.156.15.50
cd /opt/virtual-pal

# 查看可用的 SHA 版本
docker images virtual-pal-backend

# 回滚到指定版本（比如 a1b2c3d）
docker tag virtual-pal-backend:a1b2c3d virtual-pal-backend:latest
docker tag virtual-pal-frontend:a1b2c3d virtual-pal-frontend:latest
docker compose up -d

# 验证
curl http://localhost:8000/api/v1/health
```

> 服务器上默认保留最近 3 次部署的 SHA 版本，所以至少有 3 个版本可以回滚。

---

## 七、运维常用命令

### 日志查看

```bash
# 服务器上实时看日志
docker compose logs -f

# 只看后端
docker compose logs -f backend

# 只看 Redis
docker compose logs -f redis
```

### 重启某个服务

```bash
docker compose restart backend
```

### 查看当前运行版本

```bash
docker images virtual-pal-backend
docker ps --format "table {{.Names}}\t{{.Image}}"
```

---

## 八、注意事项

### 8.1 安全

- **不要**把 `SERVER_SSH_KEY` 写在代码里
- 服务器建议用密钥登录，**不要**用密码登录 SSH
- SSH 私钥只存 GitHub Secrets，不要外传

### 8.2 数据库持久化

Redis 数据存在 volume `redis_data` 中。`docker compose down -v` 会删除数据。正常重启/更新不会丢。

### 8.3 文件说明

| 文件 | 用途 |
|---|---|
| `docker-compose.yml` | 本地开发 / CI 集成测试（含 `build:`） |
| `docker-compose.deploy.yml` | 服务器部署版（仅 `image:`，CD 自动传送） |
| `.github/workflows/ci.yml` | CI 流水线 |
| `.github/workflows/cd.yml` | CD 流水线 |

---

## 九、排错

| 问题 | 排查方法 |
|---|---|
| CI 不触发 | 检查 ci.yml 的 `on.push.branches` 是否包含当前分支 |
| CD 不触发 | 检查 CD 是否依赖 CI 且 CI 是否通过 |
| SCP 传送失败 | SSH 密钥配对了？`SERVER_HOST` IP 正确？防火墙 22 端口开放？ |
| SSH 连接失败 | 服务器 IP 对不对？私钥对不对？ |
| 容器启动后退出 | `docker compose logs` 查看具体报错 |
| 页面访问不了 | 服务器防火墙 80/8000 端口开放了吗？ |
| 回滚后没生效 | 确认 tag 打对了，`docker compose up -d` 重新读取了标签 |

---

## 十、下一步

1. 确认 SSH 密钥已配置 → 公钥在服务器，私钥存 GitHub Secrets
2. 服务器上创建 `/opt/virtual-pal` 目录
3. 把 `develop` 合并到 `main` → 观察 Actions 跑完 CI → CD
4. 访问 http://82.156.15.50 和 http://82.156.15.50:8000/api/v1/health
