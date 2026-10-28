"""Regression tests for public deployment gates; synthetic data is never a public bank."""
import hashlib
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def load(path):
    spec = importlib.util.spec_from_file_location("gmf_public_bank_gate", ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class PublicReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "modules.sqlite3"
        self.gate = load("scripts/verify-public-bank.py")

    def seed(self, placeholder=False):
        asset_dir = self.root / "assets" / "test-doc"
        asset_dir.mkdir(parents=True)
        image = asset_dir / "test.png"
        image.write_bytes(b"synthetic test image")
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        with sqlite3.connect(self.db) as con:
            con.executescript("""
              CREATE TABLE questions (question_id TEXT,document_id TEXT,scope TEXT,publication TEXT,current_version_id TEXT,payload TEXT);
              CREATE TABLE question_versions (version_id TEXT,payload TEXT);
              CREATE TABLE v4_meta (version_id TEXT,payload TEXT);
              CREATE TABLE documents (document_id TEXT,payload TEXT);
              CREATE TABLE assets (asset_id TEXT,payload TEXT);
              CREATE TABLE answer_keys (version_id TEXT,revision INTEGER,payload TEXT);
            """)
            con.execute("INSERT INTO questions VALUES (?,?,?,?,?,?)",
                        ("q1","d1","bank","approved","v1",json.dumps({"publication":"approved"})))
            con.execute("INSERT INTO question_versions VALUES (?,?)",
                        ("v1",json.dumps({"stem":"What is 2+2?","options":[{"label":"A","text":"4"},
                         {"label":"B","text":"[Visual option B; inspect original question crop]" if placeholder else "5"}]})))
            con.execute("INSERT INTO v4_meta VALUES (?,?)",
                        ("v1",json.dumps({"published_at":"test","published_by":"test-reviewer","safe_assets":["a1"]})))
            con.execute("INSERT INTO documents VALUES (?,?)",("d1",json.dumps({"reuse_confirmed":True})))
            con.execute("INSERT INTO assets VALUES (?,?)",
                        ("a1",json.dumps({"relative_path":"test-doc/test.png","sha256":digest})))
            con.execute("INSERT INTO answer_keys VALUES (?,?,?)",
                        ("v1",1,json.dumps({"status":"Verified","label":"A"})))
        return image

    def test_missing_bank_fails(self):
        result = self.gate.check(self.db,self.root,369)
        self.assertFalse(result["passed"])
        self.assertEqual(result["published"],0)

    def test_synthetic_valid_bank_passes_minimum_one(self):
        self.seed()
        result = self.gate.check(self.db,self.root,1)
        self.assertTrue(result["passed"],result["errors"])
        self.assertEqual(result["checked_assets"],1)
        self.assertEqual(result["verified_answer_keys"],1)

    def test_369_question_release_gate_blocks_one_valid_question(self):
        self.seed()
        self.assertFalse(self.gate.check(self.db,self.root,369)["passed"])

    def test_placeholder_options_block_release(self):
        self.seed(placeholder=True)
        result = self.gate.check(self.db,self.root,1)
        self.assertFalse(result["passed"])
        self.assertTrue(any("placeholder" in e for e in result["errors"]))

    def test_missing_question_image_blocks_release(self):
        image = self.seed()
        image.unlink()
        self.assertFalse(self.gate.check(self.db,self.root,1)["passed"])

    def test_tampered_question_image_blocks_release(self):
        image = self.seed()
        image.write_bytes(b"tampered")
        self.assertFalse(self.gate.check(self.db,self.root,1)["passed"])

    def test_missing_verified_answer_blocks_release(self):
        self.seed()
        with sqlite3.connect(self.db) as con:
            con.execute("DELETE FROM answer_keys")
        self.assertFalse(self.gate.check(self.db,self.root,1)["passed"])

    def test_unconfirmed_license_blocks_release(self):
        self.seed()
        with sqlite3.connect(self.db) as con:
            con.execute("UPDATE documents SET payload=?", (json.dumps({"reuse_confirmed":False}),))
        self.assertFalse(self.gate.check(self.db,self.root,1)["passed"])

if __name__ == "__main__":
    unittest.main()
