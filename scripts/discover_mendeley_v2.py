"""Probe official Mendeley Data v2 metadata without inventing source checksums.

This is a bounded, read-only public-metadata discovery task. No token or
unvalidated third-party URL is accepted. A failed probe is a research blocker,
NOT evidence that the spreadsheet contains no records.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

DATASET = "ytmwsf2997"
VERSION = 2
URLS = (
    f"https://api.data.mendeley.com/datasets/publics/{DATASET}/files?version={VERSION}",
    f"https://api.data.mendeley.com/datasets/{DATASET}?version={VERSION}",
    f"https://api.mendeley.com/datasets/{DATASET}?version={VERSION}",
)
MAX_METADATA = 1_000_000


def _read_public_json(url: str) -> dict | list:
    if url not in URLS:
        raise ValueError("unregistered Mendeley Data public metadata URL")
    headers = {
        "Accept": "application/json,application/vnd.mendeley-public-dataset.1+json",
        "User-Agent": "DOCOMO-Research-Source-Discovery/1.0",
    }
    token = os.environ.get("MENDELEY_ACCESS_TOKEN", "").strip()
    if token:
        if "\n" in token or "\r" in token:
            raise ValueError("invalid Mendeley access token")
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request,timeout=15) as response:
        if response.status != 200:
            raise ValueError(f"metadata endpoint returned HTTP {response.status}")
        content=response.read(MAX_METADATA+1)
    if len(content)>MAX_METADATA:
        raise ValueError("provider metadata exceeds 1 MB limit")
    decoded=json.loads(content.decode("utf-8"))
    if not isinstance(decoded,(dict,list)):
        raise ValueError("provider returned unexpected JSON top-level type")
    return decoded


def _files(record):
    if isinstance(record,list):
        return record
    if isinstance(record,dict):
        for key in ("files","results","items","data"):
            if isinstance(record.get(key),list):
                return record[key]
    return []


def inspect_public_metadata() -> dict:
    attempts=[]
    valid_files=[]
    for url in URLS:
        try:
            record=_read_public_json(url)
            entries=_files(record)
            info={
                "api_host":urlparse(url).hostname,
                "api_path":urlparse(url).path,
                "provider_status":"HTTP_200_JSON",
                "top_level_type":type(record).__name__,
                "keys": sorted(str(k) for k in record)[:30] if isinstance(record,dict) else None,
                "candidate_file_count":len(entries),
            }
            for file in entries:
                if not isinstance(file,dict):
                    continue
                content=file.get("content_details") or {}
                if not isinstance(content,dict):
                    content={}
                name=file.get("filename") or file.get("name")
                uid=file.get("id")
                sha=content.get("sha256_hash") or file.get("sha256_hash")
                size=content.get("size") or file.get("size")
                file_record={
                    "filename":name,
                    "file_id":uid,
                    "reported_sha256":sha,
                    "reported_size_bytes":size,
                    "download_url_available":bool(content.get("download_url")),
                    "provider_metadata_endpoint":url,
                }
                if isinstance(name,str) and name.lower().endswith(".xlsx"):
                    valid_files.append(file_record)
            attempts.append(info)
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,
                OSError,ValueError,UnicodeError,json.JSONDecodeError) as error:
            attempts.append({
                "api_host":urlparse(url).hostname,
                "api_path":urlparse(url).path,
                "provider_status":"unavailable",
                "error_type":type(error).__name__,
                "http_status":getattr(error,"code",None),
                "message":str(error)[:250],
            })
    return {
        "dataset":"10.17632/ytmwsf2997.2",
        "actual_xlsx_bytes_retrieved":False,
        "source_digest_independently_pinned":False,
        "metadata_attempts":attempts,
        "provider_reported_workbooks":valid_files,
        "status":"source_file_metadata_discovered_download_not_yet_verified" if valid_files
                 else "provider_original_workbook_not_yet_retrieved",
        "warnings":[
            "Metadata availability is not original source-byte retrieval.",
            "Version-2 XLSX checksum and exact worksheet schema must be verified before the empirical importer can run.",
            "Do not promote this corpus in catalog/evidence_registry.json without the original v2 bytes.",
        ],
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("mendeley-v2-public-metadata.json"))
    args=parser.parse_args()
    report=inspect_public_metadata()
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
