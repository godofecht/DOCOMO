"""Synthetic provider replies only; do not confuse mock metadata with real v2 source."""
import importlib.util
import json
import os
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

module = Path(__file__).resolve().parents[1] / "scripts" / "discover_mendeley_v2.py"
spec = importlib.util.spec_from_file_location("docomo_mendeley_probe", module)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class FakeHttpResponse:
    status = 200
    def __init__(self, response):
        self.response = response
    def read(self, n):
        return self.response[:n]
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass


class MendeleyDiscoveryTests(unittest.TestCase):
    def test_only_fixed_documented_provider_endpoints_accepted(self):
        with self.assertRaisesRegex(ValueError, "unregistered"):
            probe._read_public_json("https://example.com/stolen-token")

    def test_auth_is_optional_and_not_leaked_in_report(self):
        captured = []
        def fake_open(request, timeout):
            captured.append(request)
            return FakeHttpResponse(b'{"results":[]}')
        with patch.object(probe.urllib.request, "urlopen", side_effect=fake_open):
            with patch.dict(os.environ, {"MENDELEY_ACCESS_TOKEN":"test-secret"}, clear=False):
                parsed = probe._read_public_json(probe.URLS[0])
        self.assertEqual(parsed, {"results":[]})
        self.assertEqual(captured[0].get_header("Authorization"), "Bearer test-secret")

    def test_http_401_is_not_pretended_to_be_empty_dataset(self):
        def deny(url):
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)
        with patch.object(probe, "_read_public_json", side_effect=deny):
            report=probe.inspect_public_metadata()
        self.assertEqual(report["status"],"provider_original_workbook_not_yet_retrieved")
        self.assertFalse(report["source_digest_independently_pinned"])
        self.assertFalse(report["actual_xlsx_bytes_retrieved"])
        self.assertEqual(len(report["metadata_attempts"]),3)
        self.assertTrue(all(x["http_status"]==401 for x in report["metadata_attempts"]))

    def test_filename_metadata_does_not_claim_original_bytes(self):
        original={
            "files":[{
                "filename":"user_stories_estimates.xlsx",
                "id":"synthetic-uuid-not-real",
                "content_details":{"sha256_hash":"0"*64,"size":1000,
                                   "download_url":"https://example.org/synthetic"},
            }]
        }
        def fake_read(url):
            if url==probe.URLS[0]:
                return original
            raise urllib.error.HTTPError(url,401,"Unauthorized",{},None)
        with patch.object(probe,"_read_public_json",side_effect=fake_read):
            report=probe.inspect_public_metadata()
        self.assertEqual(report["status"],"source_file_metadata_discovered_download_not_yet_verified")
        self.assertEqual(report["provider_reported_workbooks"][0]["file_id"],"synthetic-uuid-not-real")
        self.assertFalse(report["source_digest_independently_pinned"])
        self.assertFalse(report["actual_xlsx_bytes_retrieved"])


if __name__=="__main__":
    unittest.main()
