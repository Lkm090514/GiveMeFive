# MF-V3-SOURCE-AUDIT

审查日期：2026-10-21。范围仅限本次实际可读文件。历史报告里的“通过”没有自动转成此次测试结论。

## 可用性

| 对象 | 状态 | 本次证据与限制 |
|---|---|---|
| 初始 Work 工作目录 | MISSING | 盘点时未找到项目源码、ZIP、package.json、AGENTS.md；后续从可用资料取得下列包 |
| Fusion V2 reviewed | PARTIAL | 实际解压并读取；有根 app.js、learning-store.js、study-sessions.js、mind-flow/、旧 AS 源码；缺少运行与测试所需 data/course.json、完整课程数据和 assessment 构建目录 |
| GiveMeFive source-only | PARTIAL | 读取源码包；存在 MF/Store/旧 AS 文件，不能据文件名推定为最新完整项目 |
| 旧 Mind Flow 源码 | AVAILABLE | 实际找到 mind-flow/{app.js,flow-core.js,v1.js,index.html,styles.css,fusion-mf.css,pathline-bridge.js,blueprints.js} |
| V2.1 补丁、Git bundle、验收材料 | AVAILABLE | 37 个 ZIP 条目，含 patch、bundle、测试 JSON、历史截图和验收报告 |
| 可运行的完整 V2.1 | PARTIAL | bundle HEAD=436958d3d5b0b4885a23601cfd168e982e75a3ef，但缺前置 91c241484f843b6227a29f72193ec8062bf4790f；clone 失败；git apply --check 也失败，未强行套用 |
| V2.1 历史验收结果 | REPORT_ONLY | 读取 2026-10-11 报告；其浏览器截图及设备限制只代表当时测试 |
| 2026-10-18 AS V2 完整源码 | MISSING | GiveMeFive/Fusion/Assessment/AS-V2 文件检索未找到该完整交付；没有核实到提交 87074bd 的对象或源码 |
| 最新 Fusion / 最新 MF 与 AS V2 的集成状态 | UNKNOWN | 旧包不能证明 Windows 最新项目现状 |
| AS V3 v0.2 独立模块 | AVAILABLE | 实际读取 gmf-assessment-v3-modules/docs/CONTRACTS.md 与包内容；仅为模块，不当作主项目 |
| 旧 UI 资源 | PARTIAL | 可读旧 CSS/HTML；共享 design-tokens.css 内容存在 V2.1.patch 新增文件段中，未形成已恢复运行版 |
| 数据契约与测试 | PARTIAL | 可读旧 Store、Study Session、桥接与 MF 脚本；课程数据缺失导致一组旧测试无法执行 |

精确原包哈希见 `evidence/input-archives.json`。解包后 441 个文件清单见 `evidence/source-inventory.json`。部分历史 ZIP 中文路径编码异常（Fusion reviewed 的旧 AS 目录），本次保留实际路径，不通过改名伪造相同基线。

## MF 功能差异

以下路径以 `GiveMeFive-Fusion-V2-reviewed/` 为根，行号基于本次实际文件；分类是改造建议，不表示已修改旧文件。

| 功能 | 分类 | 实际代码与结论 |
|---|---|---|
| 自由计时 | FIX | mind-flow/flow-core.js:31–43 createRun/clockAdvance；app.js:191 syncClock 在后台或 120 秒无输入时停止累计，且控件直接调用 clockAdvance 的入口与该规则不一致；不等于 V3 的专注状态时间 |
| 定时模式 | FIX | flow-core.js:31–43 支持 1–240 分钟，但到零将 paused/expired 设为 true、截断 elapsed；app.js:191 使用 showModal；V3 要求非阻断提醒且继续累计 |
| 暂停与继续 | FIX | app.js:225 pauseResume；已有暂停机制，但到期恢复硬编码延长 10 分钟，与新周期规则不同 |
| 休息 | ADD | app.js:227 closeTime('break') 实际仅设 paused=true；缺独立 Resting 状态和休息累计 |
| 任务管理 | FIX | createRun.steps、app.js:186 begin/239 renderSummary/279 continue-later；任务嵌于 run，重开生成新 steps ID，非跨 Session 独立 Task |
| 子任务 | SIMPLIFY | flow-core.js:suggest/shrinkStep 与 app.js:prepare/renderPlan 支持规则自动分段、micro、小步记录；改为可选手动一级子任务，创建专注不强制先填任务 |
| 问题记录 | FIX | app.js:215–219 saveNote 写 run.notes，carryRun 仅带走未完成 step 相关 notes；没有独立解决/重开状态或跨会话问题列表 |
| 历史记录 | FIX | app.js:230–234 finish 保存到上下文相关 HISTORY，最多保留 100 条；254–262 renderHistory。新增统一 MF Records 投影，不静默截断历史 |
| Review & Repair | SIMPLIFY | mind-flow/v1.js 的 create/submit/hint/recheck/evidence 与 app.js:309–360 独立 reviewTimer；不继续作为新 MF 主流程，但保留旧数据和历史学习证据 |
| 多标签页 | ADD | app.js:113–123 从 localStorage 读取 run；begin 无跨标签原子唯一约束；learning-store.js:12–13 的 queue/known 是页面内变量，不能据此保证跨标签一致性 |
| PL/AS 关联 | FIX | pathline-bridge.js:3–9、fusion-core.js 和 app.js review context 保留 course/topic/session、来源事件；依赖完整宿主核实正式 AS question ID、路由及考试状态权威源 |
| UI 复用 | BLOCKED | 旧 mind-flow/index.html:9 加载 styles.css + fusion-mf.css；V2.1.patch:1634 起新增共享 design-tokens.css 并修改入口。最新组件版本尚未取得，不能做最终统一验收 |

当前源码没有证明存在 MF 在线大模型调用：旧 suggest、methodHint、judge 是本地规则。精简时也需移除不属于 V3 的自动分段与教学判断流程，但不能把“旧规则函数”误报成已接入 AI。AS V3 Answer Engine 原文件不改动。

## 计时与清除的关键风险

1. 旧 `study-sessions.js:4–13` 的活动计时依赖 visible/lastInput，并按学习模式计入 daily_seconds；不能直接拿它表示 MF 的“专注状态时间”。
2. 旧自由 MF 和 reviewRun 各有独立计时。新版必须由同一共享引擎供各视图读取，不能保留互相叠加的多个计时器。
3. `learning-store.js:14 reset()` 会清空 state、ledger、sessions、pending_sync。**禁止**把它接到“清除 MF 历史”。本次清除模块只输出 MF 已结束会话删除计划，保留 Tasks/Blockers，并标记被清除会话引用。
4. 旧 clockAdvance 仅按 wall clock 差计算。新版使用宿主提供的 wall/monotonic/runtime 三项检查点；恢复只保留已提交段，不根据离线截止时间补算。
5. AS v0.2 的 question_id/version_id 属于模块命名空间，`ExternalLink.confirmed=false` 不能冒充正式 GMF exercise_id。新版 Blocker 单独保存 namespace/question_id，未知课程关联保持空。

## 视觉系统审查

| 项 | 可读依据 | 阶段 B 的处理 |
|---|---|---|
| 颜色、深浅色 | V2.1.patch 新增 design-tokens.css 的 --gmf-bg/surface/text/muted/primary 和 dark 规则 | 核实最新文件后直接继承；不从本报告复制成新配色体系 |
| 字体 | 同一补丁的 --gmf-font，映射到三模块 body | 使用最新共享变量 |
| 间距、圆角、阴影 | --gmf-space/radius/shadow | 复用宿主值 |
| 顶栏和容器 | --gmf-header-height/content-width/gutter；suite-topbar、suite-topbar-mf、suite-assessment-topbar | 保持真实模块导航，MF 内部仅四页 |
| Button/Card/Input/Dialog | 旧 styles.css、index.html 与 design-tokens.css 覆盖层 | 旧 CSS 组件与覆盖层并存，不能称为已确认的完整统一组件库；取最新宿主组件 |
| 响应式 | 补丁包含 860px/560px 媒体规则 | 只作已知线索；新 Focus/Tasks/Blockers/Records 横竖屏尚未实现 |
| 沉浸与迷你计时器 | 未找到符合 V3 规范的实现 | 只做共享会话的视图，不创建计时实体；不依赖全屏 API |

本阶段未新增 CSS、页面或品牌样式，未做真实 iPad/Safari 验收，也未以历史图片代替此次 UI 验收。

## 旧测试实际复跑

- `scripts/check-mf.cjs`：退出码 0，验证旧行为；其中“到时暂停”的通过不意味着符合 V3。
- `scripts/check-mf-review-v2.cjs`：退出码 0，旧 Review & Repair 核心规则可执行。
- `scripts/check-mf-v1.cjs`：退出码 1，缺 `data/course.json`。这是输入缺失阻塞，没有通过。

完整标准输出/错误见 `evidence/legacy-checks.json`。新模块测试另列，二者不混计。
