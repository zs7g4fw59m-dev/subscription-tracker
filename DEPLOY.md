# 订阅管家 — 微信小程序上架指南

> **当前测试地址**：`https://guardian-dear-aims-travelling.trycloudflare.com`（Cloudflare Tunnel，长期有效）
> 
> **注意**：已将端口从 5000 改为 8765，因为 macOS 的 AirPlay 接收器占用 5000 端口。

## 第一步：部署后端到公网

后端需要 HTTPS 域名（微信小程序强制要求）。

### 方案 A：Railway / Render（推荐，免费额度够用）

```bash
# 1. 在 railway.app 或 render.com 注册账号
# 2. 连接 GitHub，导入本项目
# 3. 设置启动命令（注意端口变量）：
gunicorn server:app -b 0.0.0.0:$PORT
# 4. 获得域名如 https://xxx.railway.app
```

### 方案 B：阿里云 / 腾讯云 ECS

```bash
# 1. 购买云服务器，安装 Python 3.9+
# 2. 上传代码
scp -r subscription-tracker/ user@server:/opt/
# 3. 安装依赖
pip install -r requirements.txt
# 4. 配置 Nginx + gunicorn + Let's Encrypt HTTPS
# 5. 启动
gunicorn server:app -b 127.0.0.1:8000 -w 2 --daemon
```

### 方案 C：本地测试用 ngrok

```bash
ngrok http 5000
# 获得临时 HTTPS 域名，如 https://abc.ngrok.io
```

---

## 第二步：注册微信小程序

1. 打开 [mp.weixin.qq.com](https://mp.weixin.qq.com)
2. 注册小程序账号（需身份证/营业执照验证）
3. 在「开发 → 开发管理 → 开发设置」获取 **AppID**
4. 在「开发 → 开发管理 → 服务器域名」添加后端域名到 **request合法域名**

---

## 第三步：配置小程序代码

1. 编辑 `miniapp/project.config.json`，将 `YOUR_APPID_HERE` 替换为你的 AppID
2. 编辑 `miniapp/app.js`，将 `baseURL` 改为你的后端域名：

```js
globalData: {
  baseURL: "https://your-server.com",  // 改这里
}
```

---

## 第四步：上传小程序

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
├── app.py              # Flask 后端
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
