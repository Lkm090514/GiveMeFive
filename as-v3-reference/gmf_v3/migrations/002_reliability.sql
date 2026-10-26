CREATE TABLE IF NOT EXISTS answer_dependencies(
 derived_answer_key_id TEXT NOT NULL REFERENCES answer_keys(answer_key_id),
 source_answer_key_id TEXT NOT NULL REFERENCES answer_keys(answer_key_id),
 PRIMARY KEY(derived_answer_key_id,source_answer_key_id)
);
CREATE INDEX IF NOT EXISTS dependencies_source ON answer_dependencies(source_answer_key_id);
CREATE TABLE IF NOT EXISTS answer_changes(
 change_id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES question_versions,
 old_answer_key_id TEXT, new_answer_key_id TEXT NOT NULL REFERENCES answer_keys(answer_key_id),
 root_answer_key_id TEXT NOT NULL, created_at TEXT NOT NULL, acknowledged_by TEXT,
 payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS changes_pending ON answer_changes(acknowledged_by,created_at);
CREATE TABLE IF NOT EXISTS import_jobs(
 job_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES import_batches, ordinal INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('queued','running','imported','needs_review','failed')),
 attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
 lease_owner TEXT, lease_until REAL, payload TEXT NOT NULL, result TEXT,
 UNIQUE(batch_id,ordinal)
);
CREATE INDEX IF NOT EXISTS jobs_claim ON import_jobs(status,lease_until);
INSERT OR IGNORE INTO answer_dependencies(derived_answer_key_id,source_answer_key_id)
 SELECT a.answer_key_id,s.answer_key_id FROM answer_keys a
 JOIN json_each(json_extract(a.payload,'$.evidence_ids')) j
 JOIN answer_evidence e ON e.evidence_id=j.value
 JOIN answer_keys s ON s.answer_key_id=json_extract(e.payload,'$.details.matched_answer_key_id')
 WHERE json_extract(e.payload,'$.kind')='trusted_match';
