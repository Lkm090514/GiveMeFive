# V4.2 教材恢复、CI 与私人预览增量验收

日期：2026-10-27（北京时间）。基线为 GitHub 最新合并 f747763，保留该次 MF 与访问门禁修复，未回退到 V4.1。

## 已提交的修复

- b1c0ff0：从原始源码 ZIP 按明确 source-root 恢复缺失资源；仅提取当前运行时清单中且 SHA-256/字节数一致的文件；保留最新程序，不导入旧后端、配置或私人数据。
- 修正合并后 MF ui.mjs、view.mjs 的陈旧哈希。清单生成器更新程序哈希，保留既有教材哈希；已存在但损坏的教材会报错，不能通过重新计算哈希掩盖问题。
- 纳入先前清单遗漏的 reading-content.json、exercises.json、chapter-reviews.json、figures.json、textbook.js。前四项还与既有 baseline-sha256.json 一致。
- 新增受鉴权的 HTTPS 资源树恢复：直接使用现有私人站，不需要购买服务器或把教材放入公开仓库。令牌只从环境变量读取，使用 OAI-Sites-Authorization；禁止匿名下载、跨站跳转、覆盖有效源码及使用哈希不符的资源。
- a3cbe0d：访问失败后取消后续下载；损坏 ZIP 返回明确 ERROR，不输出堆栈。新增恢复、清单、权限与错误处理回归测试。
- c482fda：线上实测发现某个 PDF 分片一次响应哈希不符，重新请求与原包一致。为瞬时网络/503/429/哈希异常加入最多 3 次重试，每次仍须通过原始字节数和 SHA-256；401/403 等权限失败立即停止，持续损坏仍失败。相关测试更新为 22 passed。

## Pathline 实际内容

7 Units / 41 Topics；当前清单 1,225 项，全部在本地及部署打包前通过 SHA-256 和字节数校验。相较上一清单 1,220 项新增的 5 项是已有教材索引，不是生成教材。

原有 576 张页图、503 个阅读区域、1,331 条原始习题、899 道 Topic 去重引用、328 个图索引、4 个 Supplement、13 个本章习题入口继续保留。原 PDF 分片及 Topic 内容没有改写。原用户文件本来缺少印刷页 863–874，仍保留披露，未补造。

CC BY-NC-SA 4.0 与 OpenStax/Rice University、图注署名保留。教材仅同步到已有 owner-only 私人 Sites；公开 GitHub 仅提交程序、哈希清单和测试，未提交教材或令牌。

## 真实测试结果

- 完整 Node 前端：88 passed、0 failed、0 skipped（a3cbe0d）。
- 本地完整 Python：101 passed（b1c0ff0）；追加两项异常路径后，相关恢复/清单测试 20 passed（a3cbe0d）。未把这两次结果相加冒充一次完整运行。
- GitHub Actions 实跑： https://github.com/Lkm090514/GiveMeFive/actions/runs/40469618772 ，提交 c482fda。
  - MF 独立测试：39 passed、0 failed、0 skipped。
  - 后端核心：102 passed、3 deselected；这 3 项在独立 LibreOffice job 中全部 3 passed，因此完整后端 105 项被实际执行。
  - 完整前端 job：失败于资源恢复；Node 完整套件未执行。
  - 严格课程审计 job：失败于资源恢复；资源审计未执行。
  - 两个失败 job 的真实原因：`Missing or invalid GMF_COURSE_ASSETS_TOKEN; anonymous resource downloads are forbidden`。因此整体 CI 仍为 failure。
- 本地/打包严格教材审计：1,225 / 1,225，41 Topics，无失败。

## 已实际发布的私人站

https://gmf-fusion-dev-20261021.lkm31620.chatgpt.site

在 iPad Safari 打开，使用拥有本项目的同一 ChatGPT 账号登录。站点访问策略是 custom，仅 owner 一个账号、无外部访客；没有改成 public。未经登录访问会进入登录门禁。完整教材与新版 PL/MF 已发布；学习记录仍保存在当前浏览器，不能声称已经实现云同步。

最终 Sites 源码提交：e84814e379c6a9b83e2684be61c4308b11df6002（私人 Sites 源仓库，区别于公开 GitHub 开发分支）。
部署：appgdep_6ae05522ba408191b79a924a42bdacd3，状态 succeeded，版本 3。发布前严格校验全部 1,225 项；首次发布的程序不一致已重新同步修复，以本版本为准。

该托管不能运行当前 Python + LibreOffice 后端。Assessment 的真实上传、解析、考试保存仍需该后端；本次没有用前端假数据冒充，也没有删除模块。故这是完整教材 PL/MF 私人验收版，不是完整 AS 在线版。学生独立校对确认页仍属此前未完成功能。

浏览器：在同一发布源码的内部预览实测新版 MF 无任务启动、计时与暂停（01:26）；原教材 Topic 1.1 的检索入口可打开，并实际检索 vector 得到正文与图注结果。布局模拟 834×1194、1194×834、768×1024、390×844 均 PASS，最小可见按钮高度 44px；这些是桌面 Chrome 模拟，真实 iPad Safari 尚待本人验收。内部 terminal.local 不是交付网址。

## 线上资源下载的独立实测

通过同一私人站服务鉴权，在只含 Git 跟踪公开源码的干净目录中，恢复 **1,134 项**私有资源，连同 **91 项**现有程序/元数据共 **1,225 项**全部通过当前清单校验，用时 **224.02 秒**。同时核对线上非 HTML 程序资源哈希；HTML 的 index 路径由托管规范化跳转，因此该独立程序哈希检查不包括 HTML，打包前检查包括所有 HTML。

匿名请求 course.json 与 reading-content.json 均为 403；服务访问通过 OAI-Sites-Authorization，令牌未落盘。结果见 `private-host-verification.json`。这是真实线上鉴权下载实测，**不是 GitHub Actions 成功**的替代品。

首次全量下载中一个 PDF 分片出现瞬时哈希不符，独立重取与原包相同；补充最多三次重试后上述完整恢复通过。没有修改任何预期哈希来适配错误响应。

## CI 最后缺少的一次配置

代码已内置上述私人站作为默认资源地址，格式 tree，鉴权 sites。无须重新上传 ZIP，也无需另买存储。

1. 打开仓库 Settings → Secrets and variables → Actions → New repository secret。
2. Name：`GMF_COURSE_ASSETS_TOKEN`。
3. Value：该私人 Sites 的**服务访问 Bearer 令牌本体**，不带 `Bearer ` 前缀；对应请求头 `OAI-Sites-Authorization: Bearer <token>`。不是 GitHub PAT、ChatGPT 密码、站点网址或源码仓库临时写入令牌。
4. 保存后，在上述失败运行选择 Re-run failed jobs；也可在同一开发分支手动 Run workflow。

当前 GitHub 连接器不提供 Secrets 写入接口；执行环境也无已登录 gh CLI。因此本轮无法替用户写入这个 Secret，不能声称 CI 已全绿。服务访问令牌由 Sites 管理能力提供；本轮已在内存中使用它验证访问，不写入公开文档、源码或构建包。若用户侧 Sites 管理界面不提供服务令牌导出，需要受支持的安全凭据交接/Secrets 配置通道；仅填网址不能解决。

如已有 GMF_COURSE_ASSETS_URL，应将其更新为上述私人站地址，或删除以使用默认值。若有旧变量 GMF_COURSE_ASSETS_FORMAT / GMF_COURSE_ASSETS_AUTH，分别设为 tree / sites，或删除以使用默认。旧 ZIP 资源主机仍可通过 zip / bearer 配置，但本轮默认私人站已不需要重新打教材 ZIP。

尚未验证：Secret 配置后的 GitHub 远程完整前端/课程校验、私人站登录后的真实 iPad Safari、完整 AS 在线后端。
