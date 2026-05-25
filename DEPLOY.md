# 订阅管家 — 微信小程序上架指南

> **当前测试地址**：`https://guardian-dear-aims-travelling.trycloudflare.com`（Cloudflare Tunnel）
> 
> **注意**：已将端口从 5000 改为 8765，因为 macOS 的 AirPlay 接收器占用 5000 端口。
> 
> **本地服务**：Flask :8765 + cloudflared tunnel（自动重启配置在 ~/Library/LaunchAgents/）

## 快速部署到生产环境

### 方式一：GitHub + Railway（推荐，免费额度够用）

```bash
# 1. GitHub 认证（需要浏览器授权，无法自动化）
gh auth login --hostname github.com --git-protocol https --web

# 2. 创建仓库并推送
gh repo create subscription-tracker --public --source=. --remote=origin --push

# 3. 部署到 Railway
# 访问 railway.app → New Project → Deploy from GitHub Repo
# 选择 subscription-tracker，自动部署
```

**或者用一条命令**（GitHub 认证后运行）：

```bash
gh auth login --web && \
gh repo create subscription-tracker --public --source=. --remote=origin --push && \
open "https://railway.app/new"
```

### 方式二：直接使用当前隧道（零配置）

当前 cloudflared 隧道已就绪，HTTPS 公网可访问。适合开发测试。

```bash
# 查看当前隧道 URL
grep trycloudflare.com /tmp/cloudflared.log

# 重启隧道
pkill cloudflared
cloudflared tunnel --url http://localhost:8765 &
```

### 方式三：阿里云 / 腾讯云 ECS

```bash
scp -r subscription-tracker/ user@server:/opt/
ssh user@server "cd /opt/subscription-tracker && pip install -r requirements.txt && gunicorn server:app -b 127.0.0.1:8000 -w 2 --daemon"
# 然后配置 Nginx + Let's Encrypt HTTPS
```

---

## 注册微信小程序

1. 打开 [mp.weixin.qq.com](https://mp.weixin.qq.com)
2. 注册小程序账号（需身份证/营业执照验证）
3. 在「开发 → 开发管理 → 开发设置」获取 **AppID**
4. 在「开发 → 开发管理 → 服务器域名」添加后端域名到 **request合法域名**

---

## 配置小程序代码

1. 编辑 `miniapp/project.config.json`，将 `YOUR_APPID_HERE` 替换为你的 AppID
2. 编辑 `miniapp/app.js`，将 `baseURL` 改为你的后端域名：

```js
globalData: {
  baseURL: "https://your-server.com",  // 改这里
}
```

---

## 上传小程序

1. 下载安装 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. 打开 `miniapp/` 目录
3. 预览调试，确认功能正常
4. 点击「上传」提交代码
5. 登录 mp.weixin.qq.com → 版本管理 → 提交审核
6. 审核通过后发布

---

## 目录结构

```
subscription-tracker/
├── app.py              # Flask 后端（含 80+ 商户识别引擎）
├── server.py           # 生产 WSGI 入口
├── requirements.txt    # Python 依赖
├── data.db             # SQLite 数据库
├── templates/          # Web 版前端
├── static/             # Web 版静态文件
└── miniapp/            # 微信小程序前端
    ├── app.js / .json / .wxss
    ├── pages/index/
    └── project.config.json
```
