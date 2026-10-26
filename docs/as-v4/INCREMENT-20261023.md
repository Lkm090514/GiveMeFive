# 2026-10-23 增量交付与回滚

本版本沿用完整 GiveMeFive Fusion + AS V4。基线是 `5acb7d2714c0213e2579960cbbe9904b0e395c62`，目标提交见完整包 `RELEASE-GIT.txt` 和增量包 `increment-manifest.json`。没有发布到 Render、chatgpt.site 或其他公网环境。

## 使用方式

完整包：解压 `GiveMeFive-Fusion-AS-V4-Source-Lite.zip`，保留完整目录结构，双击 `Start-GiveMeFive.cmd`。Python 3.11/3.12、安装依赖和本地身份说明见根目录 `开始使用-AS-V4.md`。前端和 Python API 由同一入口提供；不能只用静态文件预览替代后端。

增量包适用于上面明确的 V4 基线，不包含教材等未变资源：

1. 关闭正在运行的 GiveMeFive Python 窗口。按现有 Settings 导出浏览器学习备份；不要清除浏览器数据。
2. 将增量 ZIP 解压到项目外的独立目录，完整保留 `payload` 与 manifest。
3. 在增量目录执行 `py -3 Apply-Patch.py "C:\实际路径\GiveMeFive-Fusion-AS-V4"`。
4. 脚本先检查全部涉及文件的基线 SHA-256；存在本地修改就输出冲突并停止，不先覆盖部分文件。重复应用相同版本不再写入。
5. 脚本在项目相邻的 `GMF-update-backups/时间戳/` 保存被替换的文件、一致性 SQLite 副本和 `receipt.json`。成功后按原方式启动；新增表自动创建。`receipt.json` 记录实际目标提交，旧 ZIP 自带的基线 `RELEASE-GIT.txt` 不作为增量后的唯一版本标识。

完整包、增量包都不含私人 runtime、学生试卷、访问凭据、虚拟环境、Docling 评估包或模型缓存。原必需教材、576 个页面图像及迁移文件保留。

## 数据库变化

- V3 新增 `003_import_segments.sql`：`import_segments` 与 `import_segment_heads`，关联原 ImportQueue 任务，记录页段状态、尝试次数、缓存哈希。旧 V3 迁移保持。
- V4 新增 `004_review.sql`：可选修正/复查状态与身份隔离的步骤图引用。它不替代 `v4_wrong`、`v4_answers`、QuestionVersion 或 Learning Ledger。
- 现有答案、题目版本及评分不可变约束保留。QuestionVersion 增加可空 `source_section`，旧记录兼容读取；新会话保存 Topic/题型/是否未见的快照，旧记录不补造独立性。
- 浏览器 IndexedDB 不换库、不清库。Ledger 评分修订使用新事件 ID，原事实保留，读取投影选择最新评分。V2 浏览器备份没有直接覆盖 SQLite。

## 回滚

关闭服务后先单独保存当前完整 `runtime` 和浏览器备份，尤其是升级后新作答。恢复升级前 SQLite 会回退升级后的数据库记录；先保存的新副本可供之后迁移，不应删除。

Git 用户可在没有后续源码修改时执行增量包里的 `git apply rollback.patch`，然后恢复升级前 SQLite；也可以切换到明确基线。非 Git 用户按 `receipt.json` 中的相对路径，将 `backup/files/` 中的原文件复制回项目；原来不存在的新文件只在其内容仍匹配 manifest 的 `after_sha256` 时移除。随后把 `backup/databases/` 中的 SQLite 副本复制回原路径，停服状态下处理旧 `-wal/-shm`，原始 PDF/图像资源不要删除。

不能仅回滚旧 Python 代码却继续使用含新 QuestionVersion 字段的数据：旧版严格模型不认识该字段。源码与对应的数据库快照应一并恢复。新的私人试卷和作答必须先另存，以免失去升级期间的记录。旧 Learning Ledger、阅读、高亮、书签与 MF 历史不通过本轮脚本删除。

## 本轮实际验证

- 后端：46 项通过（26 项既有 V4 + 7 项分段/身份/迁移 + 13 项修正/复查/诊断）。
- V3：51 项通过。
- Fusion/MF/共享证据：48 项通过（原有 45 + 3 项评分投影与事实保留）。
- 全部日志及 JUnit 结果在 `verification/`；这些是本轮运行结果，不引用 10 月 18/20/21 日的旧通过记录代替。

桌面 Chromium 实际走通：公共练习答错、保存错因、未见公共题独立检查、24 小时复查安排、不确定题独立收藏、PL 往返原会话、Progress 证据摘要、私人 PDF 上传并拆出 6 道自编测试题、答案匹配、正式考试刷新恢复、多标签考试锁、真实 2 分钟到期自动交卷。结果为 1 错 / 5 未答 / 0 未评分；考试后 MF 仍暂停，等待用户手动恢复。无答案、服务重启、重试和用户隔离等边界由自动化测试覆盖。

浏览器测试使用自编数据，不冒充正式 AP 公共题库。没有执行 iPad Safari 或 Windows 设备级验收，也没有把桌面尺寸模拟写成 Safari 通过。完整 196 页练习册的解析检查另见 `PDF-WORKBOOK-196.md`。

## 未完成与限制

1. 正式公共题库仍为 0。真实练习册已隔离解析，369 条都缺可靠答案；366 道需视觉/公式核验，目录 Topic 候选尚未转为已确认解题标签，不能整体公开发布。
2. Docling 标准模型、MinerU 模型的真实公式效果对照未完成；现有原图裁剪保真优先。没有 AI 模型凭据或云端跨设备同步的验证。
3. V2 真实旧学生数据迁移适配器没有实现；当前任务不强制迁移，旧备份与旧数据保持。默认延迟 24 小时，暂没有恢复 V2 可调间隔设置界面。
4. 初版诊断为描述性统计，5 题阈值及 30% 错误阈值未经真实学生数据校准。已见/未见判定也无法证明学生在站外是否获得帮助。
5. Windows 说明已更新，但需用户恢复 Windows 后设备验收；iPad Safari 待后续。没有本轮公网部署或 HTTPS 预览。
