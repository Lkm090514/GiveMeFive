# 当前源码基线审查

日期：2026-10-21

|资料|状态|实际证据与使用方式|
|---|---|---|
|恢复的原 Fusion 网站|AVAILABLE|原 Site pathline-ap-mechanics；源码提交 ccc6dbf3f8c9996984fe6c941bbce92ab607e2ac；本次仅复制其 dist 到独立开发目录|
|Fusion V2 reviewed 历史 ZIP|PARTIAL|有应用源码，但缺课程数据/完整 AS 构建，不作为当前可运行基线|
|V2.1 patch/bundle/报告|AVAILABLE|git apply --directory=dist --check 有冲突；完整输出 V21-patch-check.txt。未宣称 V2.1 已整包应用|
|MF Stage A v0.1.0|AVAILABLE|mf-stage-a-reference 原件保留；dist/mind-flow/v3/core 逐字节复用，测试验证|
|PL 教材资源|AVAILABLE|实际恢复 7 Units、41 Topics、4 Supplement、13 章节入口、1331 习题索引、576 图像资源|
|Assessment 历史源码|AVAILABLE|assessment-source；原可运行构建在 dist/assessment；两者不冒充 AS V2 87074bd|
|2026-10-18 AS V2 87074bd|MISSING|未取得，未合并|
|AS V3 独立模块|AVAILABLE|历史交付已核查，本轮不接入|
|Windows 更新的 Fusion 主项目|UNKNOWN|无法访问 Windows 电脑；等待实际源码，不推断其内容|

## 原站结构

- `index.html`、`app.js`：现有 PL/Progress 主入口，保留导航和业务。
- `shared-shell.js/css`、`pathline-base.css`、`fusion.css`：既有顶部导航、颜色、字体、卡片、按钮、主题和响应式布局。
- `learning-store.js`：givemefive-learning-v1，state / ledger / sessions / pending_sync 四个既有 store。
- `mind-flow/index.html`、`app.js`：旧 Focus；`review.html`、flow-core/blueprints/v1：Review & Repair。
- `assessment/index.html`、assets、learning-bridge：原 Assessment；评分及构建 assets 未改。
- `data/*.json`、assets/pages、source/pdf-viewer：原教材和题目资源；原始公式图像、页码映射未重做。

## MF 差异分类

|功能|分类|源码证据与本轮处理|
|---|---|---|
|自由计时|FIX|旧 mind-flow/app.js elapsed/clock；接入 Stage A session.mjs 已确认分段|
|定时专注|FIX|保留模式，Focus 可编辑 focus/rest；到期不强制跳转|
|暂停继续|FIX|host.mjs + 原生事务；恢复时丢弃未知间隔|
|休息|ADD|独立 Resting 分段，不记入专注或任务|
|任务继续与完成|KEEP|旧 steps 导入，新增跨 Session Tasks|
|手动拆分|SIMPLIFY|entities.mjs 仅一级子任务，无 AI|
|问题记录|KEEP|迁入 Blockers，保留原 notes；跨会话保存|
|历史恢复|FIX|旧 run 原文备份；V3 持久化重建并暂停|
|Review & Repair|SIMPLIFY|旧源码和数据保留，四主页面不增加第五页；Records 提供旧原文查看|
|多标签页|FIX|LearningStore.atomicModule + SessionCoordinator；跨连接原生事务串行|
|PL/AS 稳定关联|ADD|现有 course/unit/topic ID；AS 复用相同题干/选项/图像的 SHA-256 标识，不复制题库|
|视觉复用|KEEP|沿用既有主题及组件；ui.css 仅控制 MF 内容布局|
|真实 iPad 生命周期|BLOCKED|当前没有真实设备控制，必须用户在 Safari 验收|

## 安全基线

开发副本初始提交 `8c04e7f487db6ba1fd15b754f1abff30dabc231b`，本地分支 `dev/pl-mf-v3`。原 Site、原恢复目录与 Stage A 历史 ZIP 均未覆盖。本次新建的是同一网站源码的隔离开发预览，不是重建 GMF。
