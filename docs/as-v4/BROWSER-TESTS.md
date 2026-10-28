# Browser E2E — 2026-10-22

Environment: actual remote desktop Chromium, supervised same-origin HTTP preview with the real Python API and SQLite, isolated QA principals/database. No screenshots or viewport sizes are represented as iPad Safari device testing.

Observed:

1. Original Fusion loads 7 Units/41 Topics and 899 deduplicated textbook exercises, with original navigation and MF pages.
2. Administrator browser uploads a real authored PDF containing two MCQs, one FRQ and a shared diagram. Queue progresses queued→completed; summary shows total 3, MCQ 2, FRQ excluded 1, publishable 2, exceptions 0, answer-unconfirmed 0. Bulk publication succeeds.
3. Administrator creates an actual two-question, 0.5-minute MCQ paper; duration is configurable.
4. Student has only Practice/Exam/Mistakes in AS navigation and no admin entrance.
5. Topic 2.5 + related comprehensive selection creates a two-question fixed practice. Wrong option A→check locks the response and shows source key B.
6. Refresh restores selected answer and checked state. PL links for two core Topics (2.2 and 2.5) are shown; opening PL 2.5 and returning restores the original practice/check state.
7. Retrying B retains original incorrect A and subsequent correct B. Mistakes retains one current stable Question entry and two history records. Related-topic practice excludes its source Question and uses actual available count.
8. MF begins on the original Fusion page and continues into AS selection as the same visible focusing session. Starting formal Exam pauses MF, hides its entry, and displays only the independent countdown and MCQ controls.
9. Exam answer A and review flag survive refresh. A second real browser tab opens MF and shows persisted paused state with no resume controls while the exam lock is held.
10. The exam tab is closed and reopened by its exact session URL. Selected A/flag remain and countdown is near 3 seconds, not reset. At expiry the result shows automatic timeout submission: correct 0, incorrect 1, unanswered 1, ungraded 0. MF stays paused after the result.
11. Student PDF import (latest clarified product flow) actually uploads the mixed PDF, automatically creates an owner-private two-question paper, and opens directly into practice without any answer-key editor. Original source keys are processed server-side. Public and private scopes remain distinct in API tests.
12. Native IndexedDB harness executes 8/8 real-browser checks: preserving old state, multi-module commit, all-or-nothing rollback, concurrent MF start, persistent exam pause, second controller blocked by lock, no auto-resume, stable ledger event idempotency.

Additional tests added after user clarification: no-key student upload retains selected option as ungraded; private PDF mistakes query administrator public bank by confirmed Topic and solution-type metadata; exact source question copies are excluded. See backend tests and the final delivery report for whether each was additionally verified through UI.

Not completed: physical iPad Safari, physical OS sleep/termination, quota exhaustion, production ChatGPT auth, production Python HTTPS deployment and real cross-device PL/MF data sync. Live external model answering/classification not exercised because no model credentials were supplied. Browser fixture auth is test-only and is absent from normal local startup.

Final clarification checks actually observed through UI:

- Student uploads own PDF, gets a private two-MCQ paper automatically, opens it in practice with no correct-answer editing step.
- Student uploads a no-key one-MCQ PDF. Its interrupted import is recovered as attempts=2, completed, unconfirmed_answers=1. Selecting A and checking displays selected A, correct answer pending, ungraded; no score or forced key-setting.
- The earlier V3 keyword classifier mislabeled an F=ma question as kinematics. V4 now obtains solution types from explicit required equations or reviewed/model solution analysis; keyword hints stay internal and do not become asserted solution-type matches. Unknown types remain unclassified.


## 2026-10-22 本次承接：连续同类型练习

使用监督预览的真实 Python 服务和 SQLite，桌面 Chromium 页面操作：

1. 恢复上一轮学生无答案 PDF 会话：选项 A 保留，已检查锁定，正确答案待确认、未评分；Topic 2.5 和牛顿第二定律/合力加速度题型可见。
2. 点击相关练习，选择相同解题类型、题数 1；进入公共题库 QUESTION 1。选 B、检查、完成后正确 1。
3. 结果页显示原范围 2.5、相同解题类型、已安排 1、剩余 1。刷新后该信息和继续按钮仍在。
4. 继续下一组请求 10 题，仅返回实际剩余的 QUESTION 2，未重复 QUESTION 1。选 B、检查、提交。
5. 再次继续显示 0 道未练题，服务端返回耗尽提示，弹窗内可见；没有创建重复组。
6. 勾选“允许重做本轮已练过的同类题”，成功开始包含 2 题的同类型新练习。

修复了第 5 步最初发现的错误提示被 modal 背景遮挡问题，刷新后重测提示可见。
本次未重新执行前文的原生 IndexedDB 8 项，也未执行物理 iPad Safari 或系统休眠测试。

## 2026-10-23 管理员公共题库

桌面 Chromium、本地监督预览、真实 Python + SQLite，使用上轮隔离 QA 数据：2 道自编题，不代表正式题库。

1. 管理员页显示总数 2、发布 2、答案待确认 0、结构异常 0，覆盖 2/41；全部来源于当前 QA 数据，不从旧报告填充。
2. 展开原题 1，核对复合解题类型并填写依据。保存后刷新，人工类型保留。
3. 按 Topic 2.5 + 受力分析筛选，正确返回 1 道题；筛选与题量由后端查询提供。
4. 打开题型修订记录，显示原题版本、复合类型、日期与核对依据。
5. 保持筛选只有 1 题，按原始来源发布试卷；实际发布 2 题，并在 Exam 列表确认 2 题、45 分钟。
6. 保存弹窗保持至后台数据刷新完成，复测保存后原筛选仍为匹配 1 题，避免快速操作被旧页重绘清空。

没有使用该浏览器执行真实 iPad Safari 验收，没有生成对外预览或部署线上版本。
