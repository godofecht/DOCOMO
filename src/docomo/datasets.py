"""Download pinned public research datasets without silently substituting new versions."""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

SOURCES = {
    'cocomo81': {
        'repository': 'Derek-Jones/Software-estimation-datasets',
        'commit': 'e3fbd4faa2a5aec94b06535369664c3ebbcbac39',
        'path': 'COCOMO-81.csv',
        'git_blob_sha1': '5676be4c602b0e24231eb1f9ee1b4e08c4ba0466',
        'description': '63 historical project observations; COCOMO I ratings, not COCOMO II',
    },
    'metr_early': {
        'repository': 'METR/Measuring-Early-2025-AI-on-Exp-OSS-Devs',
        'commit': '7ff2d7670235f531dff77eff58355bd77392f396',
        'path': 'data_complete.csv',
        'git_blob_sha1': 'b61294d8214aa723d2b15986ab050e516955004a',
        'description': '246 randomised AI access assignments; early 2025 developer tasks',
    },
}


def _sha_blob(payload: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(payload)).encode('ascii') + b'\0' + payload).hexdigest()


def fetch_dataset(name: str, directory: Path, offline: bool = False) -> Path:
    if name not in SOURCES:
        raise ValueError(f'unknown dataset {name}')
    entry = SOURCES[name]
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f'{name}.csv'
    if target.is_file():
        payload = target.read_bytes()
        if _sha_blob(payload) == entry['git_blob_sha1']:
            return target
        raise ValueError(f'{target}: dataset checksum mismatch; refusing stale or modified data')
    if offline:
        raise FileNotFoundError(f'{target}: pinned data not cached (offline mode)')
    url = f"https://raw.githubusercontent.com/{entry['repository']}/{entry['commit']}/{entry['path']}"
    with urllib.request.urlopen(url, timeout=35) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000 or _sha_blob(payload) != entry['git_blob_sha1']:
        raise ValueError(f'{name}: downloaded research data do not match pinned Git blob SHA')
    target.write_bytes(payload)
    return target


def provenance() -> dict:
    return {name: {**spec, 'url': f"https://github.com/{spec['repository']}/blob/{spec['commit']}/{spec['path']}"}
            for name, spec in SOURCES.items()}
