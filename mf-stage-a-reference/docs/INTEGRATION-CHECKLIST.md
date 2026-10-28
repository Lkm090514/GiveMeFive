# 正式集成输入与执行边界

本文件不是要求用户现在重新提供资料；阶段 A 已按可访问内容完成开发。阶段 B 仅在最新源码实际恢复并核实后开展，不按日期自动假定恢复成功。

## 需要的文件

| 必需输入 | 目的 |
|---|---|
| 最新 Fusion 全源码、Git 元数据/commit、package.json 与锁文件 | 确认基线和依赖；当前旧 ZIP 不足以重建最新应用 |
| 最新 mind-flow/ 或其实际替代目录 | 复用现有路由/组件，查清保留代码和可精简代码 |
| learning-store.js、study-sessions.js、fusion-core.js 或正式替代物 | 实现跨标签原子会话端口，避免第二套 Store/Ledger |
| Ledger Schema、事件校验器、Session Schema、迁移记录 | 定义执行记录与旧 repair 证据的兼容关系；不擅用 MF_SESSION_COMPLETED |
| 最新 PL 与 AS 入口、路由、global navigation、考试状态源 | PL 原页启动、迷你计时器、AS 考试锁、Blocker 返回路径 |
| design-tokens.css、主题提供者、按钮/卡片/输入框/Dialog/导航组件 | 只继承共享视觉，不重建品牌体系 |
| AS V2 10/18 完整源码（历史线索 as-v2-development / 87074bd） | 实际验证来源后再接入；该提交不能仅凭对话认定存在 |
| AS V3 v0.2 模块及真实题目 ID 映射 | 保留 AI Answer Engine；未确认 ExternalLink 不进入正式课程关联 |
| 测试所需 data/course.json 和其他课程/资源清单 | 当前旧 MF V1 脚本的缺失输入；无需把整本教材复制进 MF |
| 可供迁移演练的脱敏旧 Session/Task/Blocker/Review/Ledger 导出 | 检查丢失、重复、孤儿引用和回滚；正式用户数据先备份 |
| 真实 iPad Safari 可验收入口 | 长后台、休眠、关闭恢复、横竖屏、触控与软键盘实测 |

## 阶段 B 的顺序

1. CP0：核实实际 Git 状态，在独立安全副本/分支开发；记录基线、备份导出；不 push/deploy。
2. CP1：以最新源重新审查本报告的行号与结论，确定既有设计组件和正式数据契约。
3. CP2：把候选 reducer 接到现有原子存储，补齐 lifecycle、持有者交接、损坏数据恢复、存储失败与迁移。
4. CP3：PL 原页开始、跨文档连续、全局迷你计时器、正式 AS 考试互斥；先验证真实流程再扩 UI。
5. CP4：接 Task/Blocker/Records；独立实体跨会话保存、实际事务去重、范围受限的历史清除。
6. CP5：只保留 Focus/Tasks/Blockers/Records 四个主页面，继承最新共享组件；沉浸只切换呈现。
7. CP6：按 T01–T25 分层验收；本阶段测试可以复用，但不能当作真实浏览器/设备通过。

## 尚未完成

正式持久化和 Ledger 适配、旧数据实迁移、完整文档导航的连续会话交接、生产多标签互斥、真正的全局迷你计时器、四个 UI 页面、视觉/深浅色/沉浸验收、真实 PL/AS 闭环、浏览器进程关闭恢复、iPad Safari 均未完成。

## 回滚策略

本阶段仅隔离模块，没有正式库写入。阶段 B 必须：保留旧原始数据与可恢复导出；迁移标记幂等；回滚时先导出 V3 新数据，再撤销代码/投影关联；不得删除原 Ledger 或清空数据库。未知 schema 不降级覆盖。设备限制应留在验收报告中，而不是通过模拟窗口尺寸消除。
