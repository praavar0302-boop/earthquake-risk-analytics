"""Check the files selected by .gitignore without creating or invoking Git.

python scripts/check_publication.py
python scripts/check_publication.py --copy-to /path/to/empty/release-check
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

try:
    import pathspec
    from PIL import Image
except ImportError as error:
    raise SystemExit('Install requirements-analysis.txt before running publication checks.') from error

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {'.py', '.md', '.txt', '.toml', '.json', '.csv', '.ipynb', '.yml', '.yaml'}
PATTERNS = {
    'personal absolute path': re.compile(r'(?:/Users|/home)/[A-Za-z0-9_.-]+(?:/|$)|[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+'),
    'email address needing review': re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}'),
    'credential-shaped token': re.compile(r'\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{25,})\b'),
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'credential assignment': re.compile(r'''(?i)\b(?:api[_-]?key|password|access[_-]?token|client[_-]?secret)\b\s*[:=]\s*["']([^"'\n]{8,})["']'''),
}


def selected_files(root=ROOT):
    spec = pathspec.PathSpec.from_lines('gitwildmatch', (root/'.gitignore').read_text().splitlines())
    included, excluded = [], []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        if '.git' in path.relative_to(root).parts or spec.match_file(name):
            excluded.append(path)
        elif path.is_symlink():
            raise ValueError(f'Symlink requires explicit publication review: {name}')
        else:
            included.append(path)
    return included, excluded


def check(root=ROOT):
    included, excluded = selected_files(root)
    names = {p.relative_to(root).as_posix() for p in included}
    findings = []
    for path in included:
        name = path.relative_to(root).as_posix()
        if path.suffix in TEXT_SUFFIXES or path.name in {'.gitignore','.gitattributes'}:
            text = path.read_text(encoding='utf-8')
            # Notebook images are PNGs in base64; scan source, metadata and textual outputs.
            if path.suffix == '.ipynb':
                document = json.loads(text)
                assert all(not any(o.get('output_type')=='error' for o in c.get('outputs',[])) for c in document['cells'])
                def without_images(value):
                    if isinstance(value,dict):
                        return {k:without_images(v) for k,v in value.items() if k not in ['image/png','image/jpeg']}
                    if isinstance(value,list):return [without_images(v) for v in value]
                    return value
                text=json.dumps(without_images(document),ensure_ascii=False)
            for category, pattern in PATTERNS.items():
                if pattern.search(text):
                    findings.append({'file':name,'issue':category})
        elif path.suffix == '.png':
            with Image.open(path) as image:
                text=json.dumps(image.info,default=str)
            for category,pattern in PATTERNS.items():
                if pattern.search(text):findings.append({'file':name,'issue':f'PNG metadata: {category}'})
        else:
            findings.append({'file':name,'issue':'unrecognized binary/file type needs manual review'})
        if path.stat().st_size > 25*1024*1024:
            findings.append({'file':name,'issue':'larger than project review threshold (25 MiB)'})
    manifest=json.loads((root/'app_assets/export_manifest.json').read_text())
    hashes={**manifest['source_hashes'],**{'app_assets/'+name:sha for name,sha in manifest['export_hashes'].items()}}
    for name,sha in hashes.items():
        path=root/name
        if name not in names:
            findings.append({'file':name,'issue':'required app artifact excluded/missing'})
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            findings.append({'file':name,'issue':'app fingerprint mismatch'})
    raw=json.loads((root/'data/processed/revised/reproduction_manifest.json').read_text())
    if Path(raw['raw_file']).is_absolute() or raw['raw_file'] not in names:
        findings.append({'file':'data/processed/revised/reproduction_manifest.json','issue':'raw_file must be a bundled repository-relative path'})
    for needed in ['README.md','requirements.txt','constraints-tested.txt','requirements-analysis.txt',
                   '.gitattributes','.streamlit/config.toml','earthquake_risk_analysis.ipynb','streamlit_app.py','app_support.py']:
        if needed not in names:findings.append({'file':needed,'issue':'required publication file missing/excluded'})
    largest=sorted(included,key=lambda p:p.stat().st_size,reverse=True)[:5]
    return {'included_files':len(included),'excluded_files':len(excluded),
            'included_bytes':sum(p.stat().st_size for p in included),
            'largest_files':[{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size} for p in largest],
            'findings':findings},included,excluded


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--copy-to',type=Path,help='Copy only publication files to an empty directory outside this project.')
    args=parser.parse_args()
    report,included,excluded=check()
    print(json.dumps(report,indent=2))
    if report['findings']:
        raise SystemExit('Publication check failed; review findings. No files copied.')
    if args.copy_to:
        destination=args.copy_to.resolve()
        if destination==ROOT or destination.is_relative_to(ROOT):
            raise SystemExit('The clean-copy destination must be outside the project.')
        if destination.exists() and any(destination.iterdir()):
            raise SystemExit('The clean-copy destination must be empty; nothing will be deleted.')
        destination.mkdir(parents=True,exist_ok=True)
        for path in included:
            target=destination/path.relative_to(ROOT)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,target)
        print('Publication-only copy created. No Git repository was initialized.')
    print('PASS: eligible files scanned; app fingerprints and required files verified. No Git commands were run.')


if __name__=='__main__':
    main()
