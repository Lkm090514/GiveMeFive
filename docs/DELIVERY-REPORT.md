# GiveMeFive PL / MF 开发版交付报告

2026-10-21。以实际恢复的原 Fusion 为基线，提供完整可运行开发包。保留原网站整体设计、课程和 Assessment 构建。

## Pathline 更新

1. 原资源完整保留：7 Units / 41 Topics / 4 Supplement / 13 章节入口 / 1331 条习题索引 / 576 页图像。899 道去重习题由 Topic 直接引用，其余包含章节入口或隐藏索引；不能把 1331 说成每个 Topic 都可见的题量。历史 442 是较早的阶段数据，未按其重复导入。
2. 以原 canonical JSON 生成 41 个 Topic bundle，包含 Topic 所需正文、例题标签、图像引用及相应章节习题元数据；按 Topic 加载，不在启动时读取整套内容。大图按可见区域加载。
3. 课程 content_version：2026-10-21-378e0a8e6e。在线版本元数据优先，已下载的 Topic/图像优先缓存；整课/Unit 下载与学习数据分离。
4. 完整 PDF 仅作为独立可选下载。取消旧逻辑把全部 PDF 分块默认塞进课程下载的行为。
5. 新增教材页开始专注、快速记录问题；保留 Unit/Topic、阅读目录、习题入口、学习/收藏标记及来源页码。

## Mind Flow 完成项

- 四个真实路由：#mindflow/focus、tasks、blockers、records。
- 同一 Session：Focus、PL 迷你计时器、Tasks 切换均使用原 Stage A 引擎。
- 自由计时、可配置番茄钟、暂停/继续/休息/结束、非阻断到期提醒、CSS 沉浸模式和明确退出。
- Tasks：名称即可创建、编辑、完成/重开、一级子任务、重要标记、可选预计时间、当前任务归属关闭与切换。
- Blockers：快速记录、笔记、解决/重开、跨会话保留、Topic 返回；AS 错题按稳定题目指纹去重，保留原题入口。
- Records：会话列表与详情、任务/问题关联、专注和休息、本周汇总、七天趋势；只统计已确认分段，不推断掌握度。
- 刷新/重新运行恢复为暂停；每秒持久化检查点，后台安全暂停；超过 10 秒的未知间隔不补计。
- Native IndexedDB readwrite 事务实现生产端口；BroadcastChannel + 轮询同步标签页。没有新增数据库、Learning Ledger 或其他模块题库。
- 结束会话写入既有 sessions 和 MF_SESSION_COMPLETED 事件；稳定 event_id 去重；Progress 显示 focus，并保持原掌握度算法对 mode=focus 的排除。
- 原生事务保存旧 Focus / Review 原文，幂等迁入任务/问题。旧 elapsed 独立展示，不虚构 V3 已确认时间。
- 完整备份导出/增量导入；清除历史列表为二次确认的可恢复归档，任务、问题及 PL/AS 数据保留。

## 回归与视觉

45 项 Node 测试通过，包含原 34 项 Stage A 与 11 项新增宿主/资源回归。浏览器原生数据库 11 项检查通过。详见 all-tests.txt 和 BROWSER-TESTS.md。

原 Assessment assets 的 SHA-256 完全一致，评分、题库未修改。仅桥接文件加入考试计时权和错题引用，未接入 AS V3。实际示例考试答对 1/5，结果显示 20%。

颜色、字体、按钮、卡片、输入框、顶部导航、浅深色均来自原 Fusion；新 CSS 不定义独立品牌 tokens。Focus 用大数字和留白，Tasks/Blockers 用列表，Records 用统计与详情。真实设备验收不以桌面模拟代替。

## 未完成及边界

- 真实 iPad Safari、强制终止整个浏览器、设备睡眠、低存储/系统清理：未在真实设备验证。JS 生命周期测试不等于物理设备验收。
- 当前内部浏览器为 HTTP 预览，CacheStorage 和 WebCrypto 受限。整课/Unit 真离线下载、AS 稳定题目关联端到端需 HTTPS/localhost 复验；代码/数据依赖检查已完成。
- AS 原有识别接口及外部 AI 服务未作联网验收；保留其代码，不把旧 AS 说成 V2/V3。内部 HTTP 预览的原 AS 结果入 Ledger 依赖 WebCrypto，也不能据此宣布全链路通过。
- 原 AS 主要保存当前试卷；如果原试卷被后续试卷替换，MF 不复制题库，返回入口只能提示恢复对应 AS 备份，不能凭空复原旧题。
- 新增 MF 正文目前主要为中文；原全局语言开关与已有翻译保留。
- V2.1 整包 patch 不兼容本基线，未强行套用；具体冲突记录已附。未来以最新源码逐项核对。
- 独立域名不会自动读取原域名浏览器数据。实际用户旧数据需用户导出后增量导入；开发过程中没有访问/修改用户原站 IndexedDB。

## 交付结构

- dist：完整可运行网站和教材资源。
- assessment-source：可获得的历史 AS 源码（非 87074bd 的身份保证）。
- mf-stage-a-reference：原 Stage A 成果，未经修改。
- scripts：本地启动、课程 bundle 生成。
- tests：自动化回归与基线哈希。
- docs：版本核查、测试证据、实际修改清单、合并及回滚说明。
