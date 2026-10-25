#!/usr/bin/env python3
"""Package only runnable source, instructions, tests and required Markdown reports."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
required=[ROOT/'README.md',ROOT/'requirements.txt',ROOT/'evaluation'/'evaluation_report.md',ROOT/'evaluation'/'usage_report.md']
for path in required:
    if not path.is_file():raise SystemExit(f'Missing required file: {path.relative_to(ROOT)}')
files=required+list((ROOT/'code').rglob('*.py'))+list((ROOT/'tests').rglob('*.py'))
with zipfile.ZipFile(ROOT/'code.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for path in sorted(set(files)):
        if '__pycache__' in path.parts:continue
        # Fixed archive metadata makes packaging reproducible for identical contents.
        info=zipfile.ZipInfo(path.relative_to(ROOT).as_posix(),date_time=(2026,1,1,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
        z.writestr(info,path.read_bytes())
with zipfile.ZipFile(ROOT/'code.zip') as z:
    assert z.testzip() is None
    assert 'evaluation/evaluation_report.md' in z.namelist()
    assert 'evaluation/usage_report.md' in z.namelist()
    assert all(not n.startswith(('.env','dataset/','.venv/','.cache/')) for n in z.namelist())
    print(f'Created code.zip: {len(z.namelist())} files, {(ROOT/"code.zip").stat().st_size} bytes')
