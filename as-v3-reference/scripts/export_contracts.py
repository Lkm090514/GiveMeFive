"""Generate contracts and API docs from the actual installed implementation."""
import json,tempfile
from pathlib import Path
from gmf_v3 import contracts
from gmf_v3.service import Modules
from gmf_v3.api import create_app

names=["Question","QuestionVersion","QuestionAsset","AnswerKey","AnswerEvidence","QuestionClassification","QuestionRelation","ImportBatch","SourceRecord","SolverInput","ModelSolution"]
out=Path("docs");out.mkdir(exist_ok=True)
(out/"contracts.schema.json").write_text(json.dumps({n:getattr(contracts,n).model_json_schema() for n in names},ensure_ascii=False,indent=2),encoding="utf8")
with tempfile.TemporaryDirectory() as d:
    app=create_app(Modules(d),tokens={})
    (out/"openapi.json").write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2),encoding="utf8")
print("Exported",len(names),"JSON schemas and actual OpenAPI")
