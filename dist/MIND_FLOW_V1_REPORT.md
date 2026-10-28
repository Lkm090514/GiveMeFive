# GiveMeFive · Mind Flow V1 交付报告

日期：2026-10-07。已在原融合仓库集成，没有新建独立原型。仅接入 2.5、5.4、7.5 三节，未批量扩展 41 节 Blueprint。

使用入口：[打开 GiveMeFive](http://127.0.0.1:8767/?mf=v1#mindflow)。原预览页可以刷新一次。服务关闭后，双击本报告旁的“启动 GiveMeFive.cmd”。需要保持启动窗口打开。

1. **实际源码、基线与复用内容**

   - 融合仓库：`C:\codex项目\Pathline\fusion-v0.1`。起始分支 `fusion/v0.1`，HEAD `41d8ad0dafd16d4064c45cfc08e62a534d6b5246`，起始工作区干净。
   - 原 PL：`C:\codex项目\Pathline\app\index.html`。文件指纹与融合来源记录一致，未修改此原文件。继续使用融合版的课程目录、Topic/Exercise 状态、教材渲染、复习调度、界面翻译和学习计时。
   - 原 MF：`C:\Users\wojia\Documents\Codex\2026-10-04\mind-flow-v0-1-1-mind\outputs\Mind-Flow-最新版-2026-10-06\dist`。实际源码存在，没有独立 Git 仓库；`app.js` 的 SHA-256 文件指纹为 `639682603452e91d07a457aae547fddcac76384d2b5da2f652021f53400b3ee8`，与来源记录一致。提取复用其 `createRun`、`completeStep` 等任务推进逻辑，沿用单任务卡片与点状进度的交互方向；原完整 MF 文件保留。
   - 原 GMF：`C:\codex项目\GiveMeFive`。起始分支 `main`，HEAD `4abc8cd8824bc963901734377c654a9a9f4643f0`，起始工作区干净。Assessment 使用原 `app/page.tsx`、Button/Dialog/RadioGroup/Progress 组件及 PDF/DOCX 解析代码生成真实构建。
   - 另核实原预览实际来自 `C:\Users\wojia\Documents\Codex\2026-10-06\files-mentioned-by-the-user-1\outputs\Pathline`，HTTP 返回的源码与该副本一致。只将本地预览接回融合仓库，旧副本保留；地址仍为 `127.0.0.1:8767`，保留同一浏览器地址下的旧记录迁移入口。测试使用独立浏览器环境与 `8768`，未把测试数据写入用户记录。
   - 两个起始基线均有保留分支：`checkpoint/mf-v1-baseline-20261007`、`checkpoint/mf-v1-assessment-baseline-20261007`。

2. **修改文件与模块**

   融合仓库修改：`app.js`、`fusion-core.js`、`fusion.css`、`index.html`、`topic-content.js`、`ui-text.js`、`review-contract.js`、`sw.js`、`README.md`、`scripts/check-fusion.cjs`。

   新增：`learning-store.js`、`content-runtime.js`、`mind-flow/flow-core.js`、`mind-flow/blueprints.js`、`mind-flow/v1.js`、`scripts/check-mf-v1.cjs`、`scripts/sync-assessment.cjs`、本地启动文件、交付报告和 `assessment/` 原 GMF 构建。

   原 GMF 修改：`app/page.tsx`、`lib/pdf-browser.ts`、`.gitignore`、`PROJECT_CHECKPOINT.md`；新增 `lib/learning-bridge.ts`。原 `dist-cloudbase` 成品保留，融合构建另放 `dist-mf-integrated`。原 41 节教材数据、图片、PDF、习题引用、Priority Engine 代码均未改写。

3. **真实用户流程**

   从 Pathline 的代表 Topic 点击“进入 Mind Flow 巩固”，保留课程、单元和 Topic。也可从 Mind Flow 主入口进入这三节。

   Recall 隐藏教材，提交文字或公式；成功后做一个短应用，再独立 Recheck。不完整时进入 Repair：Hint 1 → 仍需帮助时 Hint 2 → 再需要时打开对应教材片段。获得提示后也可以直接合上提示重试。Recheck 使用不同题目，资料与提示从页面移除。

   三个结束结果：`independent_success`、`repaired_success`、`unresolved`。修正后仍失败就结束，安排更早复习，不无限循环。暂停、离开和刷新保留已保存的回答草稿与阶段；未结束的会话不产生完成事件。没有掌握度百分比或 Again/Hard/Good/Easy 按钮。

4. **三个 Blueprint 与教材映射**

   Blueprint 是每节的“练习与修正配置”。根字段只有 `core_targets / recall_prompts / application_prompts / common_errors / hint_ladder / repair_sources`。文字判断规则放在 Prompt 配置中，通用引擎不按 Topic ID 写死判断分支。

   | Topic | 检查重点 | 真实 repair source |
   | --- | --- | --- |
   | 2.5 Newton’s Second Law | 合力、质量、加速度；有符号的净力应用 | `os-reading-5.3-p203`、`os-example-5.2`（映射到 `os-reading-5.3-p205`） |
   | 5.4 Rotational Inertia | 到转轴的距离平方、各质点贡献相加 | `os-example-10.8`（p472）、`os-figure-10.19`（p473）、`ap-inertia-integrals` |
   | 7.5 Simple and Physical Pendulums | 小角条件、单摆周期、物理摆的转动惯量 | `os-figure-15.20`（p729）、`os-example-15.3`（p730）、`os-reading-15.4-simple-physical-p731` |

   这些引用经过程序验证属于相应 Topic，直接调用原 `PathlineContent` 的教材区域与 Supplement 样式；没有重新裁剪或生成教材。

   可复现的简短验收：2.5 回忆输入“ΣF=ma，F 指合力”，应用填 `3`，复查填 `4`；5.4 选择想不起来，逐级打开提示和教材，关闭后复查填 `20`；7.5 修正后复查填 `4` 会结束为 unresolved。

5. **统一账本、编号与学习时长**

   Learning Ledger 是“各系统共用的学习事实账本”。浏览器 IndexedDB 数据库 `givemefive-learning-v1` 分为 `state / ledger / sessions / pending_sync`，不是再建一套 MF 进度。旧 `localStorage` 只作为首次迁移来源与保留备份，新增历史不写回其中。

   统一编号采用真实课程 `ap-physics-c-mechanics-2026-27`、真实单元 `2 / 5 / 7`、真实 Topic `2.5 / 5.4 / 7.5`。MF 没有另建 Topic ID；其练习 Prompt 不冒充 Pathline 习题，聚合事件的 `exercise_id` 为 null。

   账本事件支持 `EXPOSURE / PRACTICE / LEARNING_REPAIR / MF_SESSION_COMPLETED / ASSESSMENT`。兼容投影仍供已有 `state.evidence` 调用方读取，保持旧阅读、练习和 MF 记录语义。重复完成事件按会话编号只接收一次。

   新 MF 事件包含 `event_id / session_id / course_id / unit_id / topic_id / exercise_id / source='MF' / type / occurred_at / started_at / completed_at`。`payload` 记录初次提取、应用结果、提示级别、是否修正、打开过的教材引用、最终独立检查、最终状态、实际活跃秒数和作答日志。接收时复核身份、时间、步骤与配置规则，保存事实，不写 mastery。

   Study Session 即“统一学习计时记录”。MF 活跃秒数进入原共享 `sessions`，与 PL learn、Assessment test 一起进入周一至周日的七天投入汇总。切后台、暂停不计时；连续两分钟无操作停止累计；跨日分配时长。会话和事件都有待同步条目。

   Assessment 保留原题号，并按题目内容生成稳定 `exercise_id`，重测同题不会更换编号。没有 Topic 标注的导入试卷只写当前课程层面的测评事实，不自动猜测所属 Topic。

6. **Pathline / Progress / Review 如何读取**

   共用账本投影与 `MindFlowV1.derived` 提供 `latest_mf_result / mf_session_count / last_review_at / next_review_at`。Pathline Topic 行、Progress 历史和 Review 队列显示最新 MF 结果；共享周图读同一学习时长。

   V1 调度采用简单规则：独立完成约 2 天后、修正后完成约 12 小时后、未解决约 3 小时后复习，并继续受原考试日期限制。原 Priority Engine 数学权重保持不变。推荐层读取事实，没有自行制造证据。

7. **在线、离线与本地保存**

   默认在线按需加载；第一次打开教材或修正资源时加载原内容索引。下载 Physics C 后，课程 JSON、576 个原页资源、完整原 PDF 等优先读取本地课程缓存。共验证 606 个缓存资源。

   应用代码在线时优先更新，断网时回退到下载的版本。课程内容放在独立 Cache Storage，用户事实放在 IndexedDB；删除课程离线缓存不会删除 MF 历史。旧浏览器记录按同一地址迁移，换浏览器或地址需要用现有备份导出、导入。

   `pending_sync` 是“等待未来同步的队列”；当前没有服务器同步实现，没有宣称云同步已完成。课程离线下载以 PL/MF 阅读与修正为范围，未承诺完整 Assessment 编辑器离线可用。

8. **视觉统一**

   总品牌 GiveMeFive。核心导航组只有 Pathline / Mind Flow / Assessment；Review 与 Progress 放在共享回看组。MF 使用现有 GMF/融合版的颜色、字体方向、按钮、卡片、留白和深色层次，不搬用考试页面布局。

   一次显示一个任务；顶部保持 Physics C 与 Topic 上下文；只有四个轻进度点。提示为次要操作。修正资料直接沿用 Pathline 内容组件。浅色延续原 Navy/Blue/Mint；深色区分页面 `#15181D`、卡片 `#20262D`、内层 `#2B343E`。沿用约 180ms 的轻反馈，兼容减少动态效果设置。新界面文字接入既有翻译体系，Prompt 与 Hint 提供中英文配置。

9. **实际验证结果**

   - A：Pathline 2.5 → 独立提取 → 应用 → 不同复查题 → independent_success；账本、Pathline、Progress 可读取。
   - B：5.4 → 提取失败 → Hint 1 → Hint 2 → 原教材资源 → 关闭资料 → 不同复查题 → repaired_success；调度与 Progress 更新。
   - C：7.5 → 修正后失败 → unresolved，结束且更早安排复习。
   - D：刷新保留三条 MF 结果、历史和调度；中途退出、刷新保留草稿且不增加完成次数。
   - E/F：桌面 1440×1000、iPad 尺寸 820×1180、手机 390×844 的浅色/深色、中英文切换通过，无水平溢出；平板和手机采用触控尺寸模拟，并验证原 Topic 阅读区域仍可操作。
   - G：原阅读、习题标记与取消、重复习题引用共享状态通过；原 41 节内容渲染与受保护的教材/图片/PDF 校验通过，原优先级权重未变。
   - 旧 evidence 和学习时长迁移通过；暂停不增加时间通过；切换主题保留原测评答案通过。
   - 下载课程、断网刷新、离线原图修正、离线 MF 保存、删除缓存后历史保留通过。
   - 原 GMF 示例考试实际完成并写入 ASSESSMENT；重测产生不同事件、相同题目编号。PDF 模块、worker、中文 CMap、字体资源可访问；DOCX 与 PDF 原解析回归通过。
   - 原生产构建和融合静态构建通过。修改范围 ESLint 为 0 错误、5 个原有警告。原 Fusion、Stabilization、MF 检查及新 MF V1 检查通过。浏览器验收没有未处理页面错误。

   验证记录与六种 MF 截图保存在本报告同目录：`browser-validation.json`、`offline-validation.json`、`migration-session-validation.json`、`assessment-validation.json`、`mf-*-light.png`、`mf-*-dark.png`。

10. **仍有的边界**

    - 文字提取采用明确的本地规则，不是完整语义理解或 AI 自动阅卷；未识别的正确表达可能进入修正。数字题按明确数值检查，不制造掌握度。
    - 没有云同步与跨设备账号合并；只有真实本地账本与待同步队列。
    - Assessment 未做新诊断系统，也未自动把导入试卷匹配到 Pathline Topic。原考试编辑器保留既有中英文混合文案；本轮中英文验收覆盖新融合导航、MF 与修正操作。
    - iPad/手机是浏览器视口和触控模拟，未进行实体 iPad/Safari 或手机实机测试。
    - 其余 38 节 MF 入口显示准备中，按本轮范围保留未接入状态。

11. **本地保存点与 Git 状态**

    融合工作分支：`feature/mind-flow-v1-integrated`。最终本地保存点名称：`GiveMeFive Mind Flow V1 integrated`。本报告随该保存点交付，确切 HEAD 见下方最终状态。

    原 GMF 分支：`feature/shared-learning-bridge`，HEAD `862d998d3ca547e8ac5f4542c0d79fd3edda2e77`，工作区干净。原 `main` 与基线保留。没有 push、deploy 或外部发布。

    最终融合 HEAD 与 `git status` 将在创建保存点后补入这份输出报告。之后停止，不扩展 41 节 Blueprint。
