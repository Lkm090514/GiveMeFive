-- Optional repair/review state augments Mistakes. Answers and the Learning Ledger remain authoritative.
CREATE TABLE IF NOT EXISTS v4_review_cases(
 owner_id TEXT NOT NULL, question_id TEXT NOT NULL REFERENCES questions,
 payload TEXT NOT NULL, PRIMARY KEY(owner_id,question_id)
);
CREATE TABLE IF NOT EXISTS v4_note_assets(
 asset_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL,
 version_id TEXT NOT NULL REFERENCES question_versions, payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS v4_answer_owner_question ON v4_answers(owner_id,question_id);
