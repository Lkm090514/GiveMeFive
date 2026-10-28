# PL Fusion V0.1 本地验收报告

日期：2026-10-07。范围：PL → Learn → MF → Evidence → PL Recalculate。GMF 只提供视觉语言。

## 修改与保留

| 模块 | 本轮结果 |
| --- | --- |
| PL 主框架 | 使用原版 index.html 的 shell、sidebar、topbar、课程切换、设置、导入和状态备份；拆出原有样式与运行代码，继续在 outputs/Pathline 内修改，没有另建产品框架 |
| 一级导航 | 总览 / 学习路径 / 复习 / 进度 / 课程 / 设置；导入移入课程内部；MF 没有一级入口 |
| 总览 | 当前最高价值任务、Priority Queue、待复习、课程状态、已接触 Topic 保留；排序显示 Priority #，没有将内部 0–100 分数当作学生成绩 |
| 课程结构 | 7 Units / 41 Topics 的原顺序、对应关系、范围与权重空值不变；只将已就绪内容加入可执行任务队列，并在 UI 明说这一筛选 |
| Priority Engine | weakness / forgetting / downstream leverage / confidence gap / overdue / exam pressure / prerequisite penalty 的计算与权重保留；仅将真实学习互动兼容到到期与遗忘判断 |
| 教材内容 | 原 region 渲染、exercise 引用、答案、题图、来源许可、页码、4 个 Supplement 全部保留；新增目录跳转与学习记录按钮 |
| Topic 滚动 | 有限高度的两个独立容器、各自 overflow、overscroll-behavior:contain；到边界后不传播；分界按钮可随时收起 / 恢复目录；未用 sticky 代替容器 |
| Mind Flow | 复用 2026-10-06 实际源码的 createRun / completeStep / skipStep、计时、暂停、恢复、methodHint、giveHelp、卡点与历史记录；新增 Topic 上下文、书面提取、自检、重试计数和回传，不调用 PL 的 recordAnswer |
| 视觉 | 已读取 givemefive-cloudbase.zip 的 CSS；继承背景 #F5F7FB、surface #FFFFFF、主字 #0C1733、Navy #142C6E、蓝 #2B65D9、Mint #55E0BD / #24C7A5、次字 #61708D、边框 #DCE2ED；不接考试布局与逻辑 |

原版 PL 的示例课程不冒充正式课程。当前只有 Physics C 为正式内置课程。原有 course registry 和本地自定义课程机制保留，推荐、进度和证据按 course_id 隔离，可以接入其他学科。Physics C 冻结数据没有提供前置依赖，本轮不自行推断；对应引擎能力保留。

按用户随后提出的修正，深色模式改为中性黑灰：页面 #101010、卡片 #191919、标签 #292929，标签字 #E0E0E0，次要字 #B0B0B0。深色侧栏、按钮与 MF 同步使用灰阶，取消亮蓝和浅薄荷绿标签。浅色模式仍沿用 GMF 视觉基线。实际读取标签与按钮前景 / 背景并复查截图，修复了浅字落在浅标签上看不清的问题。

深色标签实际对比度 11.02:1，主要按钮 9.12:1；MF 页面实际为 #101010 背景、#E8E8E8 文字。切换 PL 主题时更新 MF 上下文，避免父页面深色而巩固页仍为浅色。

默认 mastery=22 仅保留作原版内部计算先验，不在新 Topic 的用户界面展示为真实掌握度。Exposure 或 MF completion、self-check 不修改 mastery、confidence、正确答题次数。进度页明确显示尚无独立测评证据。

## 三层证据

证据即“这次实际发生了什么”的记录，不是成绩。state.evidence 区分 exposure、learning_repair、assessment。

Exposure 记录 event_id、course_id、topic_id、action、at，教材练习另带 exercise_id。action 包括 topic_opened、reading_completed、exercise_attempted；未完成内容的打开不计作学习接触。

MF → PL 最终字段：

| 字段 | 含义 |
| --- | --- |
| schema_version / type / source | 版本 1 / learning_repair / mind-flow |
| session_id / course_id / topic_id | 唯一会话、课程与 Topic；重复会话只接收一次 |
| started_at / completed_at | 本轮开始和结束时间 |
| retrieval_attempts | 实际提交的非空书面回忆次数 |
| successful_retrievals | 学习者对照教材后自行确认成功的次数 |
| retry_count | 首次提交后再次回忆并提交的次数 |
| hint_usage | 实际点击原 MF 帮助的次数；重绘提示不重复计数 |
| repair_steps | 实际提示、卡点和完成的整理步骤；每项有 kind、text、at |
| completion | 全部任务段是否完成；提前结束或跳过未回来的任务仍为 false |
| success_basis | learner_self_check；明确属于自检，未进行独立评分 |
| attempt_log | 每次实际回答、step_id、self_reported_success、retry、at |
| elapsed_ms | MF 原计时逻辑记录的实际学习时间 |

回传检查发送窗口、会话身份、课程、Topic、时间和计数一致性。字段缺失、非法计数、未来时间或错课程会被拒绝。重复回传不重复新增证据或活动分钟。

兼容规则仅更新 lastInteraction、lastStudied、review due 和遗忘状态。阅读采用现有间隔（首次默认 1 天）；有提示、未成功提取或修正时沿用原引擎短间隔 .35 天。单纯 completion、没有提取 / 提示 / 修正行为，不改变复习时间。没有成功答题奖励、没有重写权重。

assessment 只预留独立存储和读取位置；本轮没有 GMF 接收器、检测逻辑或 mastery 估计器。

## 实际验收链

在仅本机可访问的预览地址执行，未上传或部署。

| 步骤 | 结果 | 实际观察 |
| --- | --- | --- |
| 打开 Pathline | PASS | 原版框架与六个一级入口可用 |
| AP Physics C 总览 | PASS | 课程状态 3/41；新记录空间尚无掌握度显示 |
| 推荐 2.5 | PASS | 初始可执行任务 Priority #1 为 2.5 |
| 点击现在学习 | PASS | 从推荐进入正式 Topic 内容层 |
| 正文 / Figure / Example / 习题 | PASS | 打开原教材区域、Figure 5.12、Example 5.2、Chapter 5 第 4 题原图；全部入口仍引用原索引 |
| 进入 Mind Flow | PASS | 复用真实 MF，会话绑定 Topic 2.5 |
| retrieval / retry / hint / repair | PASS | 3 次书面提取、1 次真实重试、1 次原 MF 提示、卡点与整理共 3 项修正 |
| MF evidence 写回 | PASS | 父页面显示“学习证据已写回”；自检成功 2 次，completion=true |
| 返回 Pathline | PASS | 最近证据可见；没有 mastery 增益 |
| Review / Priority 可解释变化 | PASS | 2.5 安排约 8 小时后复习；下一推荐为 5.4；原因显示提示或修正需要较早复习 |
| 复习页开始复习 | PASS | 2.5 从 Review Queue 进入对应真实 MF 会话 |
| 刷新保留记录 | PASS | 复习时间与原因持久保存 |
| 左右滚动及边界 | PASS | 右滚不带左，左滚不带右，两边到底不带整页；收起按钮保留且恢复后可用 |
| 手机宽度 | PASS | 390×844 无横向溢出；目录收起后正文增宽，按钮可恢复 |
| 未处理 Topic | PASS | 1.1 实际显示内容待完成，无原文图片、无 MF 入口；其余状态由同一 guard 控制 |

验收产生的浏览器学习记录只存在本机测试预览的浏览器存储中，不写入课程默认数据或源码 ZIP。

## 三个正式 Topic

| Topic | 原文区域 | 正式习题 | 结果 |
| --- | --- | --- | --- |
| 2.5 Newton’s Second Law | 26 | 41 | PASS |
| 5.4 Rotational Inertia | 12 | 14 | PASS；Supplement 也可见 |
| 7.5 Simple and Physical Pendulums | 6 | 18 | PASS |

## 测试与限制

- check-fusion.cjs：PASS。冻结顺序、三个代表页、待完成页、教材文件哈希、证据校验、去重、completion 不增加 mastery、推荐和复习重算；与原引擎对比 27 组输入；原权重完全保留。
- check-mf.cjs：PASS。运行原版 MF 核心检查，验证任务拆分、缩小、跳过、暂停、到时、自由计时、恢复、卡点与待办保留、方法提示。
- check_textbook.py：PASS。934 PDF 页 / 929 编号页、99 Sections、442 唯一习题、289 Figure 索引、24 阅读流原图、92 唯一页图、4 Supplement；教材数据与原资产校验不变。
- 所有 JavaScript 文件语法检查：PASS。
- 浏览器实际链路无 JavaScript error；页面截图另存于本轮 outputs。

剩余 38 Topics 按要求保持 mapping-only。Assessment 与 GMF 功能按要求未实现。成功提取仍为学习者自检，不是独立测评。原版只有 HTML，没有提供 PDF / DOCX / PPTX 导入解析服务；文本导入与粘贴可用，页面明确说明限制，未自行添加后端。

应用内浏览器禁止 file 协议，因此本轮 UI 验收通过受限的本机项目预览完成。源码无需构建、无外部资源与联网依赖；直接双击模式的浏览器特定行为未进行 UI 自动化验收。文件模式与本机预览地址的浏览器记录空间可能不同，迁移请导出备份。

## 2026-10-07 交互修正验收（V0.1.1）

- AP 目标成绩默认 5，原生下拉仅提供 1–5；选 3 后刷新仍为 3。AP 导入课程同样适用，其他课程保留文字目标。PASS。
- 全屏阅读铺满页面，顶部和左侧导航、标题、目录及非教材内容隐藏；教材底色白色，没有上方黑边；退出按钮与 Esc 可恢复。采用页面全屏方式，适配应用内浏览器，不依赖浏览器全屏权限。PASS。
- 课程删除：点击删除显示课程名称及二次确认，取消保留课程；确认后移出列表，刷新仍保持；课程和学习记录可恢复。唯一课程删除后的空列表也可导入或恢复。PASS。
- 总览第一项恢复原加权掌握度公式；尚无测评时显示待测评，默认 22 不作真实证据；与“已接触 Topic”分开。冻结课程未提供考试权重，仍使用原引擎的缺省权重，不自行添加 AP 权重。已接入数量保留在课程卡片和学习路径。PASS。
- 题目尝试按钮点亮、再点取消；同一 Topic 的共享题目入口同步；刷新保持记录。取消只移除本题的尝试记录，重算阅读与 MF 留下的复习安排，保留其他证据及掌握度。PASS。
- 自动检查新增 AP 目标范围、原加权公式、初始掌握度排除、题目切换及取消后 MF 复习安排保留。原课程完整性、推荐权重与 MF 检查继续通过。

## 本地版本记录

分支（branch）：fusion/v0.1。

全部链路通过后创建本地 checkpoint commit：PL Fusion V0.1 structure + MF review integration。HEAD（本版的提交编号）及最终 git status（是否仍有未保存的源码修改）记录在同一输出目录的 Fusion交付记录.txt，避免在提交内写自己的提交编号形成循环。

本轮不 push、不 deploy，不接 GMF、不新增账号、不做云同步、不做 AI 推荐、不裁决 AP 范围、不批量处理其余 Topic，不继续第二阶段。
