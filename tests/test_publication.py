"""Publication checks without Git, network calls, fitting or source modifications."""
from pathlib import Path
import importlib.util
import sys
import pathspec
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('publication_check',ROOT/'scripts/check_publication.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_publication_inputs_and_fingerprints():
    report,files,excluded=module.check(ROOT)
    assert not report['findings'],report['findings']
    assert not (ROOT/'.git').exists()
    names={p.relative_to(ROOT).as_posix() for p in files}
    assert '.streamlit/config.toml' in names
    assert 'data/raw/usgs_earthquakes_1965_2025_m5.5.csv' in names
    assert 'data/processed/revised/region_year_features.csv' in names
    assert 'figures/revised/Real_world_map.png' in names
    assert not any(p.startswith('__pycache__/') for p in names)
    assert not any(p.startswith('figures/') and p.count('/')==1 for p in names)


def test_ignore_rules_keep_sources_and_hide_local_artifacts():
    rules=pathspec.PathSpec.from_lines('gitwildmatch',(ROOT/'.gitignore').read_text().splitlines())
    for name in ['.env','sub/.env.production','.streamlit/secrets.toml','sub/__pycache__/cache.pyc',
                 '.DS_Store','data/.DS_Store','.venv/bin/python','venv/bin/python','tmp/recovery.txt',
                 'GroupProject_backup.ipynb','GroupProject_with_CART_v0.ipynb',
                 'data/processed/earthquakes_clean.csv','figures/fig1_magnitude_distribution.png']:
        assert rules.match_file(name),name
    for name in ['earthquake_risk_analysis.ipynb','.streamlit/config.toml','requirements.txt',
                 'data/raw/chunks/events_2025-01-01_2026-01-01_m5.5.csv',
                 'data/processed/revised/earthquakes_clean.csv','figures/revised/fig1_magnitude_distribution.png']:
        assert not rules.match_file(name),name


def test_scanner_recognizes_sensitive_shapes_without_recording_values():
    unix_path='/'+'Users'+'/'+'example_user'+'/research'
    windows_path='C:'+chr(92)+'Users'+chr(92)+'example_user'
    escaped=windows_path.replace(chr(92),chr(92)*2)
    assert module.PATTERNS['personal absolute path'].search(unix_path)
    assert module.PATTERNS['personal absolute path'].search(windows_path)
    assert module.PATTERNS['personal absolute path'].search(escaped)
    assert module.PATTERNS['credential-shaped token'].search('ghp_'+'x'*36)
    assert not module.PATTERNS['personal absolute path'].search('data/raw/catalogue.csv')


def test_fingerprinted_files_are_protected_from_line_ending_conversion():
    attributes=(ROOT/'.gitattributes').read_text().splitlines()
    for rule in ['data/** -text','figures/** -text','app_assets/** -text','earthquake_risk_analysis.ipynb -text']:
        assert rule in attributes
