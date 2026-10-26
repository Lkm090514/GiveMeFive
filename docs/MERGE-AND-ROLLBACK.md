# 10 月 23 日合并与回滚

## 合并到届时确认的最新主项目

1. 在 Windows 上先确认 Git HEAD、工作区状态与 AS V2 `87074bd` / `as-v2-development` 是否实际存在。不得只根据名称认定版本。
2. 保留原目录；新建 worktree 或分支，备份浏览器/数据库及未提交文件。本开发版是旧 Fusion 增量成果，不覆盖新主项目。
3. 对照 CHANGED-FILES.txt 分组移植：Stage A 原样核心 → LearningStore 原子端口 → host.mjs 数据投影与迁移 → PL/MF 共享路由/UI → ContentRuntime 按 Topic/Unit 适配。
4. 若新主项目已有会话或迁移机制，只适配同一个引擎和 Ledger，不建立平行系统。当前 `mf-v3` 是既有 state store 内的模块键，不是新数据库。
5. 对 PL canonical IDs 和 content_version 做 diff；新增 Topic bundle 可由保留的原 JSON 重建。不要重复导入同一题、页图像和课程。
6. 新 AS 的考试生命周期和题目 stable ID 以届时实际契约为准。本版 learning-bridge 的 SHA-256 适配仅针对恢复站点的旧 AS；不要覆盖新 AS Answer Engine、评分或题库。
7. 运行 npm test、浏览器 qa.html、PL/MF/AS/Progress 路由回归，再用 iPad Safari 执行横竖屏、后台、关闭、重启、离线与配额检查。

## 数据迁移与恢复

自动迁移实现在 dist/mind-flow/v3/host.mjs 的 migrateLegacy：保存旧 mf-focus 与 mf-review 原文，读取 mindflow.session.v1/history.v1 兼容键；有 legacy_backup 后不重复迁移。无法解析的 run 原样保留并记状态。

迁移不删除旧键，不把旧 elapsed 转换成可信 V3 时间段。迁移后 Task/Blocker 保留稳定来源 ID。Records 可查看原文和导出四个 Store 的完整备份。

完整备份导入为增量方式：现有 ID 优先，新 ID 添加；整个备份另存 backup-import:* 原文。不会用导入覆盖新数据。要精确恢复到旧快照，先在独立浏览器配置/独立 localhost 端口中导入，核对数目及引用后再决定正式迁移。

## 回滚

- 网站代码：原 Site 从未发布本轮更改，直接返回原站即可。开发预览可部署其前一个确认版本；不要动原站数据。
- 本地 Git：本开发副本初始基线为 8c04e7f487db6ba1fd15b754f1abff30dabc231b；原恢复 Site 的 HEAD 为 ccc6dbf3f8c9996984fe6c941bbce92ab607e2ac。先导出数据，再在另一个目录检出基线。不要 reset --hard 用户工作区。
- 数据：保留旧 mf-focus/mf-review 原文；旧代码仍读取旧键。新增 mf-v3 可保留供未来恢复，不需要删除。回滚旧代码后新增 V3 记录不会自动显示，但不会丢失。
- 历史列表归档：在 Records 点“恢复历史列表”即可撤销；不删除共享证据。
- 内容缓存：可重新下载；删除内容缓存不触碰 LearningStore。不得用清空数据库解决迁移问题。
