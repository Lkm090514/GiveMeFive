# GiveMeFive · Mind Flow V3 — 阶段 A v0.1.0

日期：2026-10-21。**这是低耦合逻辑模块与审查交付，不是完整 MF V3 网站，也未正式集成到 Fusion。**

本次实际读取旧 Fusion V2、旧 source-only 包、V2.1 补丁与报告、AS V3 v0.2 模块。未取得 2026-10-18 的 AS V2 / `87074bd`，也未取得最新完整 Fusion。新代码全部位于单独目录；原包、旧源码、学习数据和 AS Answer Engine 均未修改。没有 push、deploy 或合并。

## 使用

需要 Node.js 20 或以上；本轮实测版本 24.19.0。没有 npm 依赖，无需安装。

```sh
cd mf-v3-stage-a
npm test
npm run demo
```

也可直接运行 `node --test tests/*.test.mjs`。示例输出展示专注超过目标仍继续、进入休息、主动继续及结束；它不是 UI 预览。

## 实际交付

| 文件 | 内容 |
|---|---|
| `docs/MF-V3-SOURCE-AUDIT.md` | 源码可用性、旧功能逐项分类、源文件证据、视觉复用审查 |
| `src/session.mjs` | 纯状态机、连续检查点计时、任务归属、独立休息、超时提醒、保守恢复 |
| `src/coordinator.mjs` | 宿主原子事务端口、单一当前会话、修订冲突、正式考试锁 |
| `src/entities.mjs` | 一级 Task、Blocker 去重/重开、路由意图、范围受限的历史清除计划 |
| `src/records.mjs` | 已确认时间段统计、重复快照去重、日界线适配 |
| `src/legacy.mjs` | 对已观察旧自由/定时结构的只读迁移投影；原 JSON 完整保留 |
| `scripts/project-legacy.mjs` | 生成独立迁移投影文件，不覆盖输入或已存在的输出 |
| `docs/CONTRACTS.md` | 候选输入输出契约、计时和并发假设、生产适配要求 |
| `docs/INTEGRATION-CHECKLIST.md` | 阶段 B 必需文件、集成次序、回滚边界 |
| `docs/TEST-REPORT.md` / `test-results.tap` | T01–T25 覆盖矩阵、实际测试原始输出与限制 |
| `evidence/` | 441 个原包文件的路径、大小、SHA-256，以及历史脚本复跑结果 |

## 重要边界

- 不含 AI、模型接口、独立 UI、课程副本、题库副本或第二套 Learning Ledger。
- 生产数据库适配器未接入。`tests/atomic-port.mjs` 是模拟事务端口，不能用于浏览器多标签页生产存储。
- 暂不写共享 Ledger 事件：旧 `MF_SESSION_COMPLETED` 表达 Review & Repair 学习证据，不能拿来表示新版单纯专注时长。
- 未迁移任何真实用户数据。Review & Repair 的原始回答与证据保持原样；不转换成新版掌握度或专注时间。
- UI、迷你计时器、真实 PL/AS 跳转、真实浏览器与 iPad 验收仍待阶段 B。

## 回滚

本阶段没有接入原项目，移走此目录即可撤销新模块。迁移工具只新建投影文件；删除投影不会删除源记录。正式集成后的回滚必须先导出集成后新产生的数据，再切回安全分支，不能通过清空数据库回滚。
