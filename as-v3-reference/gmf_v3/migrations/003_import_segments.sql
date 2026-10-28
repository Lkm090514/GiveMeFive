-- Extraction checkpoints belong to the existing import job, never to a second bank.
CREATE TABLE IF NOT EXISTS import_segments(
 job_id TEXT NOT NULL REFERENCES import_jobs(job_id), cache_key TEXT NOT NULL,
 first_page INTEGER NOT NULL, last_page INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('queued','running','completed','failed')),
 attempts INTEGER NOT NULL DEFAULT 0, relative_path TEXT, sha256 TEXT, error TEXT,
 PRIMARY KEY(job_id,cache_key,first_page,last_page)
);
CREATE TABLE IF NOT EXISTS import_segment_heads(
 job_id TEXT PRIMARY KEY REFERENCES import_jobs(job_id), cache_key TEXT NOT NULL
);
