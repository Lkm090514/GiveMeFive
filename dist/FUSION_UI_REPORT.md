# GiveMeFive Fusion 独立系统版 · 2026-10-07

本轮在已存在的融合产品上恢复 MF 的完整专注系统，并让 Pathline、Mind Flow、Assessment 成为真正独立页面；Progress 继续作为共享回看层。没有重写教材、扩展 41 个 Blueprint 或更改 Priority 权重。

## 找到并复用的基线

- Pathline 融合源码：`C:\codex项目\Pathline\fusion-v0.1`，修改前 HEAD `5ae27ba1ce432eb9a106aa8e764008351ab87a77`，工作区干净。
- 原 GiveMeFive 测评源码：`C:\codex项目\GiveMeFive`，修改前 HEAD `862d998d3ca547e8ac5f4542c0d79fd3edda2e77`，工作区干净。
- 原 Mind Flow：`C:\Users\wojia\Documents\Codex\2026-10-04\mind-flow-v0-1-1-mind\outputs\Mind-Flow-最新版-2026-10-06\dist`。融合目录中已有原版任务、自由/定时、帮助、卡点、历史、教程与恢复代码，本轮改外围页面与持久化接口，保留原任务核心。
- 原 Pathline `C:\codex项目\Pathline\app\index.html` 未改。沿用融合项目全部 41 Topic 的内容组件、OpenStax 页图、例题、图、正文片段与 Supplement。
- Assessment 直接使用原 GMF 的 `app/page.tsx`、原布局、题目编辑、选项、计时、提交与结果组件，重新构建后同步到融合目录。

## 用户现在怎样使用

顶部为 GiveMeFive、Pathline / Mind Flow / Assessment / Progress，课程和设置在次级入口。Pathline 左栏仅显示课程、单元、Topic；MF 和 Assessment 没有课程目录，也没有嵌套 iframe。

直接打开 Mind Flow，可自由学习或定时学习，不必选课程；首页可继续上一轮、查看当前任务、历史与卡点、重新查看教程。任务可编辑、排序、拆分，暂停和刷新保留进度；到时可以继续、结束或休息；未完成任务可下次继续。清空历史有二次确认。

从 Pathline Topic 进入 Mind Flow，自动携带课程与 Topic。可开始专注，也可进入 Review。Review 每次只显示一个任务：先不看资料提取，再解释/应用，卡住依次给方向与结构提示，仍卡住才调用现有教材资源，然后关闭资料做独立变式。成功和仍失败都会结束，未完成退出保存草稿，不写完成事实。

Assessment 恢复独立完整考试页面：原创建、导入入口、编辑、MCQ、倒计时、暂存、提交、00:00 自动提交、分数与错题对照。刷新恢复答案与剩余时间；结果页提供返回 Pathline、进入 MF 修正与 Progress 的真实链接。

## 三个 Blueprint 与教材映射

| Topic | 核心目标 | Repair 调用原有资源 |
| --- | --- | --- |
| 2.5 Newton’s Second Law | 合力、质量与加速度；同一物体 | `os-reading-5.3-p203`、`os-example-5.2` |
| 5.4 Rotational Inertia | 质量分布、到转轴距离平方 | `os-example-10.8`、`os-figure-10.19`、`ap-inertia-integrals` |
| 7.5 Simple and Physical Pendulums | 小角条件、周期与摆长平方根、物理摆惯量 | `os-figure-15.20`、`os-example-15.3`、`os-reading-15.4-simple-physical-p731` |

Blueprint 仍位于 `mind-flow/blueprints.js`，包含 core_targets / recall_prompts / application_prompts / common_errors / hint_ladder / repair_sources。资源由原 `topic-content.js` / Content Runtime 解析，不新写教材。Recheck 使用不同数值与情境；只开放这三个 Topic。

## 统一数据怎样落地

同源共享 IndexedDB（浏览器本地数据库）`givemefive-learning-v1`，继续沿用 state、ledger、sessions、pending_sync。模块草稿分为 mf-focus、mf-review、assessment-run；主题和语言用共享 preferences。没有新增 MF 大量 localStorage；旧数据仅读取迁移。

canonical IDs 沿用 `ap-physics-c-mechanics-2026-27`、真实 Unit 与 Topic；输入 Topic 经课程目录验证，Unit 重新从目录推导。自由学习允许 course_id / unit_id / topic_id 为 null。

PL 继续 EXPOSURE / PRACTICE；MF Review 继续三种 final_state，保存提取、应用、提示级别、实际 repair sources、后测与活跃秒数；Focus 保存 `MF_SESSION_COMPLETED` / payload.mode=focus，记录目标、已完成/待继续任务、卡点和真实时长，不冒充 Review 成功。Assessment 保存 `ASSESSMENT`，题目使用已有 gmf-内容摘要 exercise_id。没有 Topic 标签的考试不会因为从某 Topic 启动而伪造题目所属 Topic；启动上下文保留在 payload.launch_context。

完成事件、模块进度、StudySession 和 pending sync 使用一个数据库事务保存。按 event_id 去重，刷新结果页不会重复完成。pending_sync 只是未来同步队列，尚无云同步。

StudySession 共用 active_seconds / daily_seconds。MF 暂停、隐藏、离线、超过无操作阈值时不持续加时；刷新/退出不追补离开时间。Assessment 的考试截止时间与活跃学习时长分别记录：考试到时交卷，但后台时间不全部当作学习投入。

Pathline Topic 和 Review 读最新 MF Review、次数、last_review_at / next_review_at；Focus 不调整 Review 结果或制造复习证据。Progress 汇总 PL、Focus、Review、Assessment 的事实与七天投入，未绑定课程的学习也能汇总。unresolved 结束并更早安排，原 Priority 数学权重未改。

## 持久化、离线与视觉

在线按需；下载课程后优先课程缓存。Content Runtime 离线清单包含独立 MF、Review、Assessment、共享脚本及现有教材。课程缓存和用户数据库分离，删课程缓存不删学习历史。网站与 localhost、不同设备的记录各自保存，尚未自动同步。

复用 GMF 五条柱形 Logo、蓝/薄荷色、字体、按钮、卡片与留白，各系统保留自身任务布局。深色使用 background / surface1 / surface2 三层；覆盖真实考试题干、选中/未选中项、禁用按钮、提示、结果与正误答案标签。轻动效约 180ms，兼容 reduced-motion。

中英文沿现有语言体系，MF 与共享导航/Review 完整切换；原 GMF 混合语言通过兼容适配转换界面文字，题干与用户输入不自动翻译。

## 实际验证

- 2.5：Recall 与应用独立成功 → 不同 Recheck 成功 → independent_success，Pathline/Progress 可读。
- 5.4：失败 → Hint 1 → Hint 2 → Example / Figure / Supplement → Recheck 成功 → repaired_success。
- 7.5：Repair 后仍失败 → unresolved → 有界结束、更早复习；刷新结果不新建重复完成。
- Focus：从 2.5 进入、增加/排序任务、完成部分、记录卡点、暂停与刷新恢复、结束、共享投入、历史均实际操作。独立无课程的定时 1 分钟到时，结束并保留下一轮任务。
- Assessment：原示例考试、选答案、刷新保留、手动提交与 1 分钟到时自动提交均实际操作。结果刷新后仍显示 01:00，不重复写事实；错题对照与回跳可用。
- 离线：实际下载 622 个资源后关闭本轮本机 HTTP 服务，刷新课程页、进入 MF 读到原历史、进入 Review 与 Assessment 恢复结果均成功；随后已恢复服务。后台/无操作计时通过已有自动检查；本轮未进行真实网络断开时的长时间计时实测。
- 设备尺寸：Desktop、390×844 手机、820×1180 iPad；独立页面与结果页无横向溢出。是浏览器尺寸验证，不是实体 iPhone/iPad 硬件测试。
- 浅色/深色考试正文、选中项、提示/禁用态实际取色计算均超过 4.5:1；补修后的深色结果百分比 8.97:1、错误答案 9.51:1、正确答案 9.50:1。详见对比度 JSON。并非对全站每个像素的 WCAG 认证。
- `check-mf-v1.cjs`、`check-mf.cjs`、`check-stabilization.cjs`、`check-fusion.cjs`、`check-independent-systems.cjs` 全部通过。覆盖原 7 Unit / 41 Topic、内容资源、练习状态、Priority 权重、迁移、实际时长、三种结果、去重与独立页面；原 Focus 任务核心字节保护检查通过。
- 原 GMF Vite 构建成功（2193 模块）。TypeScript 全量检查仍失败：基线 ES2017 配置不支持原第 61 行正则命名组、原 DOCX 解析的 Worker/DOM Element 类型冲突；未扩大本轮范围修复。不能宣称全量类型检查通过。

## 修改模块与剩余问题

共享壳：shared-shell.js / shared-shell.css；数据：learning-store.js、fusion-core.js；页面：app.js、index.html、ui-text.js、mind-flow/index.html / app.js / review.html / v1.js；原测评：app/page.tsx、lib/learning-bridge.ts、融合 assessment/learning-bridge.js / css 及静态构建；离线：content-runtime.js、sw.js、data/app-shell.json；维护：sync-assessment.cjs、check-fusion.cjs、check-independent-systems.cjs。

原 GMF 源码未找到独立错题知识柱状图/知识分析实现，本轮保留真实错题与正确答案对照，没有虚构已恢复图表。导入链路保留原功能，但本轮未逐一回归每种 PDF/DOCX/OCR 格式与外部 AI 服务。设置的 JSON 备份沿用原共享记录导出；独立 Focus/Exam 草稿的跨地址迁移尚未纳入该备份。旧 GMF 兼容翻译仍需后续整理为统一源码词典。

本轮仅本地新分支和 checkpoint；PL/GMF 远端不 push。公网更新沿用用户已授权的网站，保留原链接与访问范围。最终 branch / HEAD / git status、ZIP 完整性及保存位置见同目录 `Fusion-源码版本.json`、`Fusion-ZIP校验记录.json` 与 `Fusion-网站发布记录.json`。
