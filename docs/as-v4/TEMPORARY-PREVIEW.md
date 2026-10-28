# GiveMeFive AS V4 临时 HTTPS 预览

日期：2026-10-23。本补丁只增加启动/分享工具，不修改产品功能，不发布或覆盖现有 chatgpt.site。

## 当前 Work 尝试结果

已下载并运行 Cloudflare 官方 cloudflared 2026.10.3，确认存在 `--allowed-mail`。已启动原 Fusion 静态资源与真实 FastAPI 后端，在一个本地 HTTP 服务提供全部页面、API、图片和上传入口。关闭 QA 身份选择入口，保留真实服务端身份校验。

实际申请邮箱保护 Quick Tunnel 失败，原始关键错误：

```
failed to request quick Tunnel:
Post "https://api.trycloudflare.com/tunnel":
dial tcp: lookup api.trycloudflare.com on 168.63.129.16:53:
dial udp 168.63.129.16:53: connect: network is unreachable
```

当前 Work 使用受限网络执行环境，cloudflared 的直接网络连接无法建立。没有生成可交付的临时 HTTPS 地址，未验证外网前端或 API，也没有用 localhost/terminal.local 冒充 iPad 可访问链接。下载程序成功不代表隧道建立成功。没有尝试解除环境网络限制。

## 实际验证

本次用启动中的真实 Uvicorn 服务和实际 HTTP 请求完成 6 组验证（未用 TestClient 替代网络）：

1. Fusion 首页、Assessment 页面和 health API 使用同一入口。
2. 未登录 API 为 401；学生管理接口为 403；QA 直登入口为 404。
3. 实际上传自编 PDF，后台任务自动解析 4 道 MCQ、提取原卷答案并发布公共题库。
4. 学生上传自编混合 PDF，排除 FRQ、自动创建私人试卷；正式考试保存选项/标记/截止时间；提交后正确记录错误和未答，显示标准答案、题型与原图。
5. 从私人试卷题目匹配公共题库同知识点/题型；两组各 2 道题，第二组无重复。
6. 无答案 PDF 保存选项并保持未评分，不误加入错题集。

测试数据隔离在临时目录，检查完成后服务停止。Linux 启动器已实际启动服务并复现上述隧道网络错误，失败后自动清理服务。没有执行真实 Windows、邮箱验证码收取或 iPad Safari 设备级验收。

## 无云账号的替代：Windows 一键分享给 iPad

需要一台可运行完整源码、可连接 Cloudflare Tunnel 的 Windows 电脑。仅持有 iPad 时，本补丁本身不能运行 Python 后端。

1. 将补丁 ZIP 的内容解压到上次完整 AS V4 源码根目录，与 `Start-GiveMeFive.cmd` 放在同一层。不要只解压到一个独立空文件夹。无需重新下载整个 159 MB 源码。
2. 已安装 Python 3.11+ 后，双击 `Preview-GiveMeFive.cmd`。首次会安装原有后端依赖并从 Cloudflare 官方 GitHub 下载隧道程序。
3. 填写唯一允许访问的邮箱。无需注册 Cloudflare/Render 账号，也不用购买域名。
4. 等待窗口打印已连接后的 HTTPS 地址。先在 iPad Safari 打开“邮箱验证入口”，输入邮箱并完成验证码；再在同一 Safari 打开窗口中的“完整验收链接”。分两步能避免邮箱验证跳转丢失访问链接的片段。
5. 使用的是原有 Fusion + 真实 Python 后端，包括管理员题库、学生 PDF、模考、错题和连续练习。初始题库是否有题，取决于该电脑 `runtime/v4` 的现有数据；源码包没有预装完整 AP 公共题库。管理员可以上传并发布题目。
6. 保持电脑联网、避免休眠、保持窗口打开。按 Ctrl+C 停止，链接随之失效；`runtime/v4` 中试卷、题库和作答保留，不自动删除。

只允许一个邮箱，不允许通配符。隧道不支持邮箱保护时启动器会停止，不会改成公开隧道。后端仍使用独立高强度访问令牌与 HttpOnly Cookie，关闭 QA 免登录入口。完整验收链接包含该电脑管理员访问权限，请仅给本人使用。

临时域名可能每次改变；PL/MF 的浏览器数据按域名隔离，不能据此声称跨域/跨设备同步。AS 个人数据在运行后端的电脑保存。此方式适用于本人临时验收，尚不是面向其他学生的生产部署。

仅回滚分享工具时可移走 `Preview-GiveMeFive.cmd` 与 `scripts/share-preview.py`，不会影响 `Start-GiveMeFive.cmd` 和原始产品。先关停分享窗口，不删除 `runtime/v4`。

官方依据：https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/ （邮箱验证码 `--allowed-mail`，无需 Cloudflare 账号；临时进程停止后访问结束）。
