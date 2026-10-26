# GiveMeFive · Mind Flow V1 integrated

在原融合源码基础上接入 Mind Flow V1 与共享学习账本。Pathline / Mind Flow / Assessment 是三个平级核心系统；Progress 是共享回看层。41 节原教材内容保留，本轮仅接入 2.5、5.4、7.5 三节 MF Blueprint。详见 MIND_FLOW_V1_REPORT.md。

在“学习路径”选择任意 Topic，即可阅读原教材、公式、原图、例题、理解检查和对应正式习题。Topic 与 Chapter 入口共用同一道题的记录。补齐内容不会自动标记用户“已学习”。

内容统计、逐 Topic/Chapter 数量、来源许可和测试结果见 **课程内容完整性报告.md** 与 **content-completeness.json**。已有 UI 操作说明见下文；旧阶段验收报告仅记录当时版本。

打开 http://127.0.0.1:8767/ 或双击 **启动 GiveMeFive.cmd**。保持启动窗口打开。当前版本需要通过本地 HTTP 预览运行，不再直接双击 index.html；无需安装新依赖。旧浏览器记录按原地址首次迁入 IndexedDB。新增学习历史不继续写入 localStorage。

- **学习路径**：每个单元显示“已学习数量 / 全部 Topic”和百分比进度条，百分比四舍五入到整数。Unit 2 学完并标记 1 节，即 1/10 · 10%。右侧 MCQ 标签是用户给定的选择题考试权重，与学习进度分别显示。
- **学习标记**：Topic 底部点击“记录本节已学习”，再次点击取消。取消只撤销该标记，习题、MF、测评与历史保留。该百分比表示内容推进，不表示掌握度。
- **习题标记**：点击“记录已完成”，选中后再次点击取消；同一道题在 Topic 与 Chapter 两个入口共享状态。按课程与唯一 exercise_id 统计。旧版“已尝试”记录保留，不自动视为完成。“留到复习”单独保存准备以后处理的题。
- **复习**：显示当前课程真实考试倒数、已到期内容、按时间排列的后续复习和留下的题。考试日期限制最晚复习时间，不改变掌握度。
- **进度**：回看周一至周日实际学习时长、课程与习题推进、MF 次数及 Topic 历史。电脑悬停、平板和手机点击柱段查看课程及学习/复习/测评明细。
- **设置**：中文和 English 立即切换；教材保持原文。每门课程独立保存考试日期、目标成绩；AP 默认 5，下拉选择 1–5。
- **阅读**：目录和正文各自滚动，目录可收起与恢复。“全屏阅读”隐藏产品栏，只显示课本；显式按钮或 Esc 退出。这是页面内全屏。
- **课程管理**：删除前二次确认；记录保留，可在“已删除课程”恢复。

计时只在教材或实际 MF 练习中累计；切后台停止，连续 2 分钟没有操作后暂停累计。每 5 秒保存一次，按本机日期分日统计，不用预估分钟，不补造过去的时长。MF 暂停与未开始阶段不计入统一复习时长。

正式题库收录所用 13 个 Chapter 的全部 1,331 道唯一章末题，其中 899 道被 Topic 引用；AP 章末入口显示 1,234 道，排除范围题保留在数据与完整原 PDF 中。177 个 Example 与 116 个 Check Your Understanding 属于正文，不计入正式题库。正文保留 315 幅 Figure，复用同一份原页图像。

TXT、MD、CSV、JSON、HTML 或粘贴文字导入沿用原版。原项目未提供 PDF / DOCX / PPTX 课程解析服务，这三种导入仍不可用；内置正式教材阅读可用。

进度保存在当前浏览器。不同浏览器、文件路径与本机预览地址可能使用不同记录空间；迁移前在设置中导出备份。MF 集成记录不覆盖独立 Mind Flow 历史。

本轮完整验收见 **课程内容完整性报告.md**；此前阶段资料见 **UIUX验收报告.md**、**Fusion验收报告.md**、**验收报告.md** 与 **fusion-provenance.json**。本地提交的准确 HEAD 与源码 ZIP 校验值见交付目录的 **Content交付记录.txt**。

开发检查：`node scripts/check-stabilization.cjs`、`node scripts/check-fusion.cjs`、`node scripts/check-mf.cjs`、`python scripts/check_textbook.py`、`python scripts/check_content_complete.py`、`python scripts/audit_content.py`。网页本身无需运行这些检查。

本轮按 Unit 使用 `scripts/complete_textbook.py --unit 1` 至 `--unit 7`，逐批核对后运行 `scripts/curate_content.py` 完成原 PDF 特殊排版修正。`scripts/build_textbook.py` 是第一阶段历史脚本，只生成三个代表 Topic，请勿用它覆盖当前完整数据。重新生产会重置内容验证标记，须重新检查再验收。

## 以下为历史阶段记录，不代表 V0.3 当前内容数量

### 上一阶段 V0.1.1 记录

本次交互更新：AP 课程默认目标 5，可下拉选择 1–5；课本“全屏阅读”隐藏页面导航、标题栏、目录与其他内容，只显示原教材，点击退出或按 Esc 恢复。习题记录按钮点亮表示已记录，再点取消，同一题的共享入口保持一致，刷新后保留状态。

课程页可删除课程，弹窗再次确认；删除后从课程列表移除，学习记录保留，可在“已删除课程”恢复。总览第一项为加权掌握度，沿用原 courseReadiness 的单元权重公式，没有测评时显示“待测评”，不会把默认 22 或 MF 完成次数当作掌握度。冻结课程没有提供考试权重，仍不自行填写，沿用原引擎的缺省权重。

双击 **index.html** 打开 Pathline。默认进入总览；学习路径按固定课程顺序显示 7 Units / 41 Topics。2.5、5.4、7.5 已接入正式教材正文与习题，其余 38 个明确标记为内容待完成。

在正式 Topic 底部点击“进入 Mind Flow 巩固”，或在“复习”点击“开始复习”。写下回忆，记录本次提取；需要时使用原有提示、重试与卡点记录。结束一轮后，证据返回 PL 并重算推荐和复习时间。自检成功与完成次数都不会增加掌握度。

Topic 的目录与正文独立滚动，分界按钮可收起并恢复目录。课程切换、目标成绩、设置和浏览器备份沿用原版 PL；导入收在“课程”内。TXT、MD、CSV、JSON、HTML 或粘贴文字可用。原版未附带 PDF / DOCX / PPTX 解析服务，暂不支持这三种格式的课程导入；内置正式教材阅读可用。

当前进度保存在当前浏览器中。换浏览器、从文件改为本机预览地址，或移动文件位置时，浏览器可能使用不同的记录空间；迁移前请在设置中导出备份。MF 集成数据使用独立的 Pathline 存储名称，不覆盖独立 Mind Flow 的历史。

本轮使用原版 PL 的主框架、原版 MF 运行代码和 GMF ZIP 的视觉配色。完整说明、验收链、证据字段与边界见 **Fusion验收报告.md**；原始来源与校验值见 **fusion-provenance.json**。不含 GMF 功能、账号、云同步、AI 推荐。

检查：`node scripts/check-fusion.cjs`、`node scripts/check-mf.cjs`、`python scripts/check_textbook.py`。网页不需要构建或安装；上述命令仅供开发验证。

## 沿用的教材第一阶段记录

教材内容作为 Pathline 内部学习页显示。“正式教材习题”和“本章课后习题”引用同一个 exercise_id，不新增或重编号题目。

课程对应关系严格使用用户给定的 2026–27 / May 2027 冻结映射。7 Units / 41 Topics 全部建立；其余 38 Topics 标记为“尚未批量处理”，不显示未经验证的正文。考试权重未在冻结要求中提供，保留为空，不自行填写。

原教材只有一份：source/university-physics-v1.pdf。网页显示从这份 PDF 渲染的原页区域，保留公式、图像、Examples、Strategy、Solution、Significance、Check Your Understanding。页面区域与 Figure 索引共用 assets/pages 下的原页文件，不重画原图。

数据均在 data 目录，使用 JSON（方便程序读取的结构化文字文件）：

- course.json：7 Units / 41 Topics、冻结选择规则、正文/习题/补充内容的引用。
- source-structure.json：教材 17 Chapters / 99 Sections，以及资源被哪些 Topic 引用。
- page-map.json：逐页核对的印刷页与 PDF 页。5 个无印刷编号的目录页记为空；17 个章首页用已核对的前后页与目录定位。附件缺少印刷页 863–874。
- assets.json、reading-content.json、figures.json：唯一原页资源、原文区域、Figure 编号/图注/独立 credit/页码。
- reading-objects.json：正文 Example、理解检查及 Strategy / Solution / Significance 标记。
- exercises.json：已提取 Chapters 5、6、10、15 的全部正式章末习题；仅三个代表 Topic 经核对的题目显示，其余保留并隐藏。
- chapter-reviews.json：所有使用到的 13 个 Chapter 习题入口。
- supplements.json：4 个用户指定的极简 AP Supplement。
- source-metadata.json：原书许可、来源、原文件校验值及缺页记录。
- textbook.js：旧版静态读取文件保留；当前运行改由 Content Runtime 按需加载原 JSON，并支持显式课程下载。

Exercise 对象含 exercise_id、source_chapter、source_section、source_number、exercise_type、question_text、subparts、image_refs、source_page、ap_unit、ap_topic、answer_ref、source_attribution。另有 render_refs（保留公式与题图的原页区域）、dependency_refs（引用上一题或正文图）及 visibility。跨节题 source_section 可为空，不猜测其归属。部分公式在 PDF 中是图形，无法完整提取为文字；question_text 是检索转录，题目原文以 render_refs 展示的原页区域为准。

正文 Figure 目前以原文区域中的图像保留，索引引用同一原页资产。本阶段未把每幅图另导出为独立文件；其余 Topic 的 Figures 仅建立索引，未完成显示区域验证。装饰照片未放进三个代表 Topic 的阅读流。

重建数据：用已安装 Python 运行 scripts/build_textbook.py，需要 pypdfium2、pdfplumber（本次使用 Codex 已有组件）。验证：运行 scripts/check_textbook.py；JavaScript 语法核对：node --check app.js。本项目直接运行静态文件，没有独立打包构建步骤。

教材第一阶段的详细结果保存在 验收报告.md。本轮 Mind Flow V1 完成后停止，未 push，未 deploy，不继续批量扩展 Blueprint。
