# GitHub CI 状态（2026-10-27，北京时间）

验证提交：`76e4c442a8e5b2411f2e5aefb3730a21fbe17c6f`。

运行：<https://github.com/Lkm090514/GiveMeFive/actions/runs/40421897745>

|任务|状态|解释|
|---|---|---|
|Backend core|成功|84 项通过；3 个 DOCX 用例由下一任务执行|
|DOCX / LibreOffice|成功|3 项全部通过，含新增学生 DOCX 流程|
|Frontend|失败，测试未执行|在恢复资源步骤发现缺少 GMF_COURSE_ASSETS_URL|
|Pathline 严格资源门禁|失败，审计未执行|同一受控资源地址未配置|

整个 workflow 结论仍为 failure，不能称为 CI 全绿。后两项不是本地通过的替代记录，也不是跳过后当作成功。

资源门禁保持严格。要使远程前端与课程审计真正运行，仍需要为 GitHub Actions 提供受访问控制的教材资源地址及相应凭据。本轮未把教材放到公开仓库，也未创建临时公开下载地址绕过限制。

此前 `356d8cb` 的 backend-core 失败来自新 DOCX 用例放错任务；`76e4c4` 已调整至安装 LibreOffice 的独立任务，新一轮两项后端检查均成功。没有删除测试或放宽断言。

最终文档更新使用 `[skip ci]`，仅添加验收说明和既有结果文件；功能与 CI 配置的已验证提交如上。文档更新跳过 CI 不被计作测试通过。
