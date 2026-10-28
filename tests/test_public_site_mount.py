"""Single-origin integration tests; the mocked preflight tests routing ONLY, not content readiness."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.bank import Bank
from backend.public_app import create_app

class PublicSiteRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        Bank(self.root)
        values = {"GMF_ENV":"production","GMF_AUTH_MODE":"password",
                  "GMF_PUBLIC_ORIGIN":"https://gmf.example.test",
                  "GMF_GATEWAY_KEY":"X" * 40,"GMF_DATA_DIR":str(self.root),
                  "GMF_MIN_PUBLISHED":"369"}
        self.env = patch.dict(os.environ, values)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_incomplete_real_bank_prevents_app_start(self):
        with self.assertRaises(RuntimeError) as error:
            create_app()
        self.assertIn("preflight failed",str(error.exception))

    def test_verified_route_wiring_serves_frontend_and_reaches_api(self):
        # Only bypass the preflight to isolate route wiring. Production never does.
        from subprocess import CompletedProcess
        with patch("backend.public_app.subprocess.run",
                   return_value=CompletedProcess([],0,stdout='ok',stderr='')):
            app = create_app()
        with TestClient(app,base_url="https://gmf.example.test") as client:
            page = client.get("/")
            self.assertEqual(page.status_code,200)
            self.assertIn("text/html",page.headers.get("content-type",""))
            self.assertEqual(client.get("/api/v4/health").status_code,200)
            # Without the internal gateway middleware this would be 403.
            self.assertEqual(client.get("/api/v4/registry").status_code,401)
            self.assertEqual(client.get("/data/course.json").status_code,200)
            # Unknown assets must not silently return a fake page.
            self.assertEqual(client.get("/assets/pages/nonexistent.webp").status_code,404)

if __name__ == "__main__":
    unittest.main()
