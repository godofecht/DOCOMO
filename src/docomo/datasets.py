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
    'hie_tasks': {
        'repository': 'FeisalAlaswad/Hie_effort_estimation',
        'commit': '09e105d5a7fb3f15e5412d688dbf79d21c42329b',
        'path': 'Task_execution_observations.csv',
        'git_blob_sha1': '428cc5078962adadd3939289b3bec0ffe6e4ead5',
        'description': '330 observed LLM-assisted task executions by 22 developers; no task identity or unaided control',
    },
    'nasa93': {
        'repository': 'Derek-Jones/Software-estimation-datasets',
        'commit': 'e3fbd4faa2a5aec94b06535369664c3ebbcbac39',
        'path': 'nasa93.arff',
        'git_blob_sha1': 'cf677e462edbe7623a5707c341c22569816aa566',
        'description': '93 historical NASA projects; COCOMO I ratings and observed person-months; potential overlap with COCOMO81',
    },
    'china': {
        'repository': 'Derek-Jones/Software-estimation-datasets',
        'commit': 'e3fbd4faa2a5aec94b06535369664c3ebbcbac39',
        'path': 'china.arff',
        'git_blob_sha1': '196189a78f70d8c84632914876077ad1f6b8aed7',
        'description': '499 historical China projects with observed effort in person-hours; N_effort is a different normalized outcome',
    },
    'desharnais': {
        'repository': 'Derek-Jones/Software-estimation-datasets',
        'commit': 'e3fbd4faa2a5aec94b06535369664c3ebbcbac39',
        'path': 'Desharnais.csv',
        'git_blob_sha1': '423ed4c60a4e6493bd41a0c62caf750ad7ec40c9',
        'description': '81 historical Canadian completed projects; actual effort person-hours, missing experience coded -1',
    },
    'kitchenham': {
        'repository': 'Derek-Jones/Software-estimation-datasets',
        'commit': 'e3fbd4faa2a5aec94b06535369664c3ebbcbac39',
        'path': 'kitchenham.arff',
        'git_blob_sha1': '3dfa1089cc4ecba24089f1b788dea98668f22a04',
        'description': '145 completed outsourcing projects, observed person-hours, original first estimates and adjusted function points',
    },
    'maxwell': {
        'repository': 'Derek-Jones/Software-estimation-datasets',
        'commit': 'e3fbd4faa2a5aec94b06535369664c3ebbcbac39',
        'path': 'maxwell.arff',
        'git_blob_sha1': '429f136d7a177dcf3bc72943579ae47e50af71d8',
        'description': '62 actual Finnish banking software projects, person-hours and function-point sizes; some publications mistakenly report 63',
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
