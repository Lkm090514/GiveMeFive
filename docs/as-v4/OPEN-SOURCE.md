# Existing open-source components reused in V4

2026-10-22. Prefer installed and V3 dependencies; no quiz-framework replacement or second parser/bank stack was added.

| Component | Use | License / primary source | Actual compatibility evidence |
|---|---|---|---|
| pdfplumber 0.11.9 | Native PDF layout, text positions, page/crop rendering through the existing V3 PDFProcessingCore | MIT — https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt | V3 regression + V4 PDF/shared-image/FRQ import tests and actual browser upload |
| pypdf 6.21.1 | Existing PDF page count, labels, document checks | Existing V3 license inventory and bundled license records | Installed pinned version; PDF tests executed |
| FastAPI 0.150.0 / Uvicorn 0.54.0 | V3 API stack reused for the same-origin Fusion API | FastAPI MIT — https://github.com/fastapi/fastapi/blob/master/LICENSE ; see bundled V3 dependency notices for transitives | Role/auth, identity isolation, actual browser requests and deadline tests executed |
| SQLite (Python stdlib) | Reuse V3 immutable Question/Version/AnswerKey/Asset/ImportQueue tables; additive V4 tables | Python/SQLite notices | Transaction/restart/concurrent-submit tests executed |
| SymPy 1.14.0 | Existing V3 bounded symbolic checking adapter | Existing V3 license inventory | V3 math tests; no live LLM result was promoted to trusted solely by an algebra check |
| LibreOffice | DOCX → PDF conversion preserves equations/images, then reuses the same V3 PDF pipeline | MPL 2.0, contribution terms MPL2/LGPL3+ — https://www.libreoffice.org/licenses/ | DOCX import test actually converts via installed soffice; executable not bundled |
| PDF.js / JSZip / Mammoth | Preserved historical AS source/assets, not new V4 import dependencies | PDF.js Apache-2.0 — https://github.com/mozilla/pdf.js/blob/master/LICENSE ; JSZip MIT/GPL option — https://github.com/Stuk/jszip | Original executable assets retained unchanged; V4 import runs server-side |
| OpenAssess adapter | Existing small V3 answer-key parsing adapter | Original attribution and license in `as-v3-reference/third_party/openassess-LICENSE.txt` | V3 tests rerun; no broad third-party exam engine copied |

Primary repositories/licenses were checked on 2026-10-22. They remain upstream projects; no blanket claim is made that an upstream package has no defects. Version pins and the exact runtime inventory are in requirements files and `dependencies.json`. Bundled V3 `LICENSES.md` and `third_party/licenses/` remain included.

Docling, KaTeX and react-quiz-component were not needed for this integration. Complex notation uses source crops instead of lossy transcription. No extra dependency was introduced merely for presentation.
