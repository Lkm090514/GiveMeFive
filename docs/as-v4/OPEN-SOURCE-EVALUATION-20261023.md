# 开源技术评估与许可证

查询日期 2026-10-23。版本来自当时官方 GitHub `releases/latest` 返回值，不代表应用已升级到该版本。应用继续使用已锁定依赖，避免因研究改变正常运行环境。

| 候选 | 查询到的版本 / 许可证 | 依赖、Windows 与实际评估 | 决策 |
|---|---|---|---|
| Docling | 2.142.0；代码 MIT，模型许可另查 | Python ≥3.10；官方支持 Windows x64/arm64。隔离安装 `docling-slim[format-pdf]==2.142.0`，约 282 MB。NativePdfPipeline 在真实 PDF 3–8、114–116、194–196 页运行成功，合计 12 页 | 保留既有可选适配入口；未加入必需依赖 |
| MinerU | 4.0.12；MinerU Open Source License（Apache 2.0 加额外条款） | 官方列出 Windows；Python ≥3.10,<3.15。基础模型约 0.8 GB；standard/advanced 约 2 GB 起，依管线需要相应内存/加速器 | 本轮未安装、未跑模型，不能声称完成复杂公式效果对照。许可也不能简单记录成纯 Apache |
| pdfplumber | latest 0.11.10；应用现有 0.11.9；MIT | 继续复用 pdfminer、Pillow、PDFium 系依赖和现有 V3 坐标/图像能力。本轮真实全书运行成功；Windows 安装仍需设备验收 | 本轮采用：增强业务分段、题目重建和原图裁剪，没有另建解析/题库框架 |
| PyMuPDF | latest 路由返回 2.0；AGPL/商业双许可 | 官方支持 Windows wheels；环境中虽然已有 1.26.6，但未将它用于应用或新增依赖 | 未确认适用许可，不引入 |
| pyBKT / examples | 官方仓库代码 MIT；未安装/训练 | 需要学生 ID、技能、作答顺序及可靠对错序列，并评估模型。官方 Windows 使用较慢的纯 Python 版本 | 数据不足，采用可解释统计，不报告掌握概率 |

Docling Native 实测：6 页 0.248 秒、3 页 0.190 秒、3 页 0.156 秒，均返回成功；分别 193/158/81 个文本项和 10/1/4 个图片项。它是无模型管线，没有布局/OCR/公式模型。文本中仍缺失原页可见的公式符号，不能据此证明完整物理题重建。标准管线在真实第 3 页尝试时因缺少 `torch` 终止；完整包依赖预检还会引入 Torch/CUDA 等大量组件，因此没有为这一轮盲目安装全部模型。没有将 Native 的速度与完整 MCQ 裁剪重建的速度直接当成同等工作量比较。

V3/PDF 原图裁剪继续作为复杂物理内容的展示依据。Docling 和 MinerU 的完整模型对照尚未完成，这是本轮技术选型的限制。评估 JSON 见 `verification/parser-comparison.json`。未把模型、评估依赖或缓存装入交付 ZIP。

官方证据：

- Docling：[仓库与许可证](https://github.com/docling-project/docling)、[2.142.0 发布](https://github.com/docling-project/docling/releases/tag/v2.142.0)、[安装说明](https://docling-project.github.io/docling/getting_started/installation/)。模型许可与代码许可分开处理。
- MinerU：[仓库](https://github.com/opendatalab/MinerU)、[4.0.12 发布](https://github.com/opendatalab/MinerU/releases/tag/mineru-4.0.12-released)、[许可证](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md)。需保留在线服务署名等额外条款；本轮未复用其运行代码。
- pdfplumber：[仓库](https://github.com/jsvine/pdfplumber)、[MIT 许可证](https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt)、[0.11.10 发布](https://github.com/jsvine/pdfplumber/releases/tag/v0.11.10)。
- PyMuPDF：[官方仓库](https://github.com/pymupdf/PyMuPDF)、[2.0 发布](https://github.com/pymupdf/PyMuPDF/releases/tag/2.0)。
- pyBKT：[官方仓库、数据映射与 Windows 限制](https://github.com/CAHLR/pyBKT)、[examples](https://github.com/CAHLR/pyBKT-examples)。

实际分发的依赖及原有许可证记录仍见 `OPEN-SOURCE.md`、`as-v3-reference/LICENSES.md` 和各包附带许可证。原 PL 教材与资源署名保持不变。
