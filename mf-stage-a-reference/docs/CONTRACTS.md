# 阶段 A 候选契约 v0.1

所有下列接口都是低耦合候选接口，**不是已确认的 Fusion 正式集成接口**。模块只处理参数/返回值，不访问任何正式数据库、localStorage、浏览器 DOM、AS API 或 Ledger。

## Session

`createSession(options, stamp) -> Ready snapshot`；`transition(snapshot, command, stamp) -> new snapshot`。不修改输入。`validateSession` 拒绝未知 schema、损坏字段、重叠时间段、坏 anchor 与不合法状态；宿主必须保留原记录并提供恢复途径，不得捕获错误后删除它。

| 输入 | 约束 |
|---|---|
| options.session_id | 宿主生成稳定唯一字符串；禁止复用历史会话 ID |
| mode | free / pomodoro |
| focus_ms/rest_ms | 默认 1500000/300000；正整数，最多 24 小时是此候选接口的防错边界，不是学习建议 |
| task_id | null 或已存在 Task ID；宿主事务必须验证引用 |
| context | course_id/unit_id/topic_id/exercise_id/source/return_to；未知留 null。不会根据某题推断课程 |
| stamp | wall_ms（纪元毫秒）、mono_ms（单调时钟读数）、runtime_id（本次运行生命周期唯一 ID） |

| command.type | 行为 |
|---|---|
| start | Ready→Focusing；重复 start 不覆盖或恢复暂停会话 |
| tick | 确认连续时间段；非持有时钟的 runtime 的 tick 无效 |
| pause / suspend / exam_start | 可累计的当前短段提交后安全暂停，后续暂停时间不计 |
| rest | Focusing→Resting，任务归属只计到切换点；不在 Paused 内偷偷开始休息 |
| resume | Paused→Focusing 延续专注周期；Resting→Focusing 开始新周期；中断前处于休息也开始新专注周期 |
| switch_task | 关闭上一任务分段、修改当前 task_id；正常连续运行中不暂停 |
| end | 封存会话；结束后 tick/end 重放不增加时间 |
| recover | 从持久化快照恢复，保留 session_id/已确认段，默认 Paused；不补算间隔 |

输出 snapshot 包含 revision、phase、segments、notices、anchor。`totals()` 与 `timerView()` 从已确认段派生数值，不另存第二份权威累计。专注与休息超时仅新增每周期一个稳定 notice，不自动暂停或切换状态。UI 需通过 notice ID 去重提醒；刷新后历史 notice 不应再次主动打扰。

## 时间与生命周期

- 建议宿主约每秒提交一次连续检查点；本内核不自行启动 setInterval。
- 同一 runtime、两个时钟增量非负且差异不超过 1000ms、相邻样本不超过 10000ms，才接受 `min(wallDelta, monoDelta)`。
- 任一条件不满足，整段不计并安全暂停；10 秒/1 秒是保守工程预设，需在阶段 B 设备实测后评估。
- 保存失败必须显示未保存状态并冻结可见累计；只显示已提交快照。不能用页面内存累计冒充已落盘时长。
- 重新加载/新运行时必须先 recover，再由用户 resume；不得把旧 anchor 带入自动续跑。
- pagehide/冻结/设备挂起由宿主生命周期层处理；不能只靠 beforeunload。已明确中断时应 suspend；遗漏事件时长间隔检查只是后备防线。
- 短于阈值、又没有生命周期信号的挂起无法仅由两个时钟完全区分。本阶段不宣称已解决所有 Safari 休眠情况，也不声称时间证明了学习投入。
- 最多会丢失尚未提交的一小段，不事后猜测补时。统计文案为“专注状态时间”。

**页内切换路由、Task、Blocker、沉浸视图不应触发生命周期暂停。** 对旧 Fusion 的完整文档跳转，还需阶段 B 实现共享引擎持有者/经验证的路由交接；不能直接把每次新页面加载都当故障恢复后就宣布“跨模块连续”已完成。本阶段该项 BLOCKED。

## 原子事务与正式考试

`SessionCoordinator(port, scope)` 的 port 属于现有宿主，不属于本模块。

```
read(scope) -> Promise<{current: Session|null, exam_ids: string[]}|null>
transact(scope, reducer) -> Promise<committedRow>
```

`reducer` 必须同步；宿主必须在同一个跨标签事务内读取最新行、检查 revision、保存 current 和考试锁。事务失败回滚；Promise 只在持久提交后完成。同一 scope 只能有一条 current。新会话替换已结束会话时，原会话归档与 current 替换必须在同一事务。拒绝复用所有历史 ID。

`start(options,stamp)` 在活动会话存在时返回原会话；`dispatch(session_id,expectedRevision,command,stamp)` 拒绝旧版本。冲突时重新读取再展示，不能无条件重试破坏性命令。后台 tick 可丢弃旧修订后等下一次检查点。外部标签的显式暂停可丢弃尚未确认的小段，不把未确认时间补上。

`examStart(exam_id,stamp)` 持久记录考试锁并暂停 MF。`examEnd(exam_id)` 仅释放对应锁，MF 仍暂停。有任意正式考试锁时拒绝 start/resume。宿主必须先持久化暂停再开放考试计时，崩溃后依据 AS 的真实考试状态核对锁；禁止让 UI 随意调用 examEnd 解除进行中的考试。

多标签通知只是促使视图重读，不是互斥锁。`tests/atomic-port.mjs` 仅模拟事务串行化，不能将它作为生产多标签实现。宿主可利用现有 IndexedDB 的事务机制，但必须先读最新源码核实 schema，不能擅自另建 Ledger 或把 Promise 队列当跨页锁。

## Task / Blocker / 路由

- `createTask(input,existing)` / `editTask(task,patch)` 返回单一任务对象；只强制名称，一级 parent_id，手动完成/重开。完成父任务不会自动完成子任务。
- `upsertBlocker(existing,input) -> {created,blocker}`；`editBlocker` 支持笔记、解决、重新打开。独立实体由宿主持久化，结束 Session 不修改问题状态。
- AS 问题去重键为 namespace+question_id；重复进入复用原记录、追加会话与版本引用，不覆盖原始版本、笔记、标题或解决状态。用户可主动重开。
- `question_id` 与 `exercise_id` 分开；不复制题面、答案或评分。关联失效时由宿主显示无法打开，不能猜路由。
- Task/Blocker 的读、去重、写也必须放入宿主原子事务；纯函数本身不提供跨标签互斥。
- `routeIntent(blocker,'PL'|'AS')` 只返回稳定 ID 和返回路径元数据；宿主白名单路由解析器负责实际导航、权限和 ID 存在性。不得直接将 return_to 拼接为任意跳转 URL。

## Records / 清除 / 迁移

`recordsSummary(sessions,dayKeys,calendar)` 返回按 session_id 最新 revision 去重的汇总。相同修订冲突拒绝统计；日界线由 calendar.dayKey/nextDayStart 决定。本周和最近七天须由宿主按用户时区生成 dayKeys，不能默认宿主 UTC 即用户日期。

`planClearMFHistory({sessions,blockers},{confirmed,confirmedAgain})` 仅生成已结束新版 MF Session 的删除 ID 和 Blocker 引用更新。任务保留；Blocker 保留并记录 removed_session_ids。活动会话、Review & Repair 原始历史、共享 Ledger、PL/AS 全部排除。UI 二次确认与事务执行尚未接入。

`projectLegacyRun(raw_json,source_key)` 只支持已实际观察的旧 free/focus run；生成稳定迁移 ID、Task/Blocker 投影、旧 elapsed 的独立字段。原 JSON 字节完整保留。不将旧 elapsed 加进 V3 已确认段，不抹掉历史数字。未知结构（包括旧 Review & Repair）只保留不误转。

`appendMigration(existing,projection)` 可重复执行；同一 source_key 内容变化则拒绝。source_key 必须来自不可变导出记录身份，不能仅使用会被覆盖的 localStorage key。正式迁移需宿主在事务中先保存原始备份、验证引用、写迁移标记与投影；本阶段未实施正式 schema 迁移。
