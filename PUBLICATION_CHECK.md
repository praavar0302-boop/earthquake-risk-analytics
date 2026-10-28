# Publication preparation check

Checked on 28 October 2026. No Git repository was initialized and no commit, push or deployment was performed.

## Completed

- Replaced the provenance manifest's machine-specific raw-data path with a repository-relative path and refreshed the app fingerprint. Raw SHA-256, package versions and analytical results are unchanged.
- Added publication exclusions for caches, local environments, credentials, recovery copies and obsolete derived files. Source datasets were not deleted.
- Added `.gitattributes` to preserve the bytes of fingerprinted files across checkouts, including the CRLF raw CSV.
- Added a project README, standard app requirements, tested dependency constraints, an analysis/test dependency file and third-party data notices.
- Scanned publication-eligible text, notebook content and PNG metadata for personal paths, email addresses and credential-shaped values. No findings remained. The scanner reports suspicious values by file/category without printing the values.
- Verified all required Streamlit artifacts are included and match their fingerprints. No fitting is needed at app startup.
- Executed all 36 notebook code cells using publication-only inputs in a temporary workspace. All 13 generated CSVs matched verified results within 1e-12 tolerance. Existing notebook/data/figure files were not overwritten by this check.
- Passed 13 app/publication tests, including all ten walkthrough stages, navigation, filters, forecast controls, pricing/reference quotes, missing inputs and publication rules. The app was also tested from a publication-only copy, outside the original project location.
- Runtime and analysis dependency dry-runs succeeded against the existing environment using `--no-index`; no packages were installed or downloaded.

## Remaining decisions / limits

- The authors have not chosen a project software license. Third-party plate-boundary attribution and license links are documented separately.
- A genuinely pristine dependency download/install and a hosted Linux build have not been performed. Tested package constraints target the existing Python 3.13 environment.
- Privacy scans are pattern-based checks, not a guarantee that every possible sensitive datum has been recognized. Excluded files remain local; do not add them manually without review.
- Catalogue retrieval date and the original one-record discrepancy remain research-provenance limitations, not runtime blockers.

## Recheck

```bash
python -m pytest -q tests
python scripts/check_publication.py
```

The selected-file inventory and sizes are calculated by the check script, rather than hardcoded here. Any future change to fingerprinted inputs requires reviewing results and refreshing the relevant app manifest or one-time exports.
