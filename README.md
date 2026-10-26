# GiveMeFive Fusion + Assessment V4.1

2026-10-24 第一阶段：原 PDF 保真作答、无答案考试、部分评分覆盖及保存恢复。正式导入与考试不调用 AI。当前开发与实测记录见 `docs/as-v4/V41-PHASE1-20261024.md`；下方历史报告不代表本轮验收。

启动完整 V4：阅读 `开始使用-AS-V4.md`，Windows 双击根目录 `Start-GiveMeFive.cmd`。真实 Python API 与现有 Fusion 在同一地址运行。

最终行为与测试：`docs/as-v4/DELIVERY-REPORT.md`。学生自己的试卷来自 PDF 自动拆题；管理员题库和学生上传分别保存。

---

以下为原 PL/MF 基线说明，保留作历史参考：

# GiveMeFive · Fusion PL / MF 开发版

2026-10-21 · 基于实际恢复的旧 Fusion 网站增量开发。不是 Windows 上 10 月 18 日 AS V2 的替代版本。

## 启动

安装 Node.js 22 或以上。解压到独立目录，在目录中执行：

```sh
npm start
```

打开 http://localhost:4173 。Windows 可双击 `Start-GiveMeFive.cmd`。不需要 npm install，不要直接双击 HTML。端口占用时通过 `PORT` 改端口。当前服务器只监听本机；iPad 请使用交付的 HTTPS 开发预览地址。

`dist/` 就是完整可运行网站。PL、MF 为可直接编辑的 JS/CSS/ES modules；Assessment 保留恢复站点的可运行构建，`assessment-source/` 为同时找回的历史源文件，不能据此声称已经取得 10 月 18 日 AS V2。未重编译或替换其题库、评分代码。

## 使用

- Pathline 打开 Topic，点“开始专注”，留在教材页面继续阅读；顶部迷你计时器与 MF 共用一个会话。
- MF：Focus / Tasks / Blockers / Records。自由计时无需任务；番茄钟可改时长，时间到仅提醒。
- Tasks 支持一级子任务、编辑、重要标记、预计时间和跨会话继续。
- Blockers 可补充笔记、解决/重新打开、返回关联教材。
- Records 显示专注/休息、七日趋势、本周总量、会话详情；可导出/导入完整数据备份。
- “课程”可下载整课或 Unit；原教材 PDF 单独下载。离线下载需要 HTTPS 或 localhost。删除内容缓存不会动学习数据。
- 暂停不计时，休息单独计时。页面路由切换不中断；进入后台主动安全暂停。刷新/休眠后未知时间不补计。
- AS 考试持有独立计时权，MF 会暂停；交卷后 MF 仍暂停。AS 原题跳转以原试卷仍保留为前提。

## 验证

```sh
npm test
```

45 项 Node 测试：34 项原 Stage A 核心测试，11 项新增集成/资源回归测试。
浏览器访问 `/qa.html`，点“运行验证”：隔离数据库原生事务测试。`/qa-layout.html` 为尺寸模拟工具，不是主应用页面。

证据、限制与具体文件见 `docs/DELIVERY-REPORT.md`、`docs/BROWSER-TESTS.md`、`docs/CHANGED-FILES.txt`。

## 数据与预览注意

记录保存在浏览器本地，没有新增云同步。独立开发预览使用新的域名，因此不会自动带入原网站本地数据。原网站记录未被移动、覆盖或清空。完整备份导入采用增量添加，遇到现有 ID 保留现有记录并归档导入原文；不会强行覆盖冲突数据。

真实 iPad Safari、设备级强制关闭/休眠、离线缓存容量及存储不足仍需实际设备验收。新增 MF 正文目前以中文为主，原站全局语言设置保留。

## 回滚与 10 月 23 日合并

请读 `docs/MERGE-AND-ROLLBACK.md`。不要把此目录覆盖到届时恢复的最新 Windows 项目中。
