# Ghost Data Still Exists — offline deletion auditor

A terminal-runnable, offline baseline for HackerRank Orchestrate October 2026.
It reconstructs identity links and timestamped evidence, applies deletion policy, and writes the required `output.csv`.
It never deletes actual customer data and makes no hosted model calls.

**Measured public-sample results: 23/32 deletion statuses correct (71.88%); 9/32 exact step sequences correct (28.12%).**
All 17 participant-created regression tests pass. The latest pass recovered one complete sequence by preserving explicitly referenced source accounts in future verification. Missing identity provenance remains a substantial limitation; this is not a claim of a fully accurate submission.
See [evaluation/evaluation_report.md](evaluation/evaluation_report.md) for metrics, failures, custom cases, and per-case results.

## Setup

Python 3.11+ and the Tesseract executable with English language data are required.
The development run used Python 3.14. Dependency installation needs internet access; subsequent audit runs are offline.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Install Tesseract with your platform's package manager:

```bash
# macOS
brew install tesseract

# Debian / Ubuntu
sudo apt-get install tesseract-ocr
```

On Windows, install Tesseract, add its executable directory to PATH, and use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.
No API key, `.env`, credentials, model download, or cloud account is needed at runtime.
Tesseract's English recognition model is installed with the executable; it reads the supplied English business screenshots.
The multilingual request classifier operates on Unicode text independently of OCR.

Place the provided `dataset/` at the repository root; it is deliberately excluded from `code.zip`.

## Run

From the repository root:

```bash
.venv/bin/python code/main.py
```

This reads the 518 evaluation requests and writes `output.csv` at the repository root, sorted by `case_id`, with exactly these columns:

```text
case_id,deletion_status,steps_json
```

Paths default relative to the source location, not the current working directory.
For a different dataset or output destination:

```bash
.venv/bin/python code/main.py --dataset /path/to/dataset --output /path/to/output.csv
```

Additional flags: `--requests`, `--cache`, and `--diagnostics`.
`--requests` can select the public sample request CSV.
The first run OCRs all 11 screenshots; later runs reuse a content-hashed local OCR cache under `.cache/ocr/`.
A clean run does not depend on that cache. No prepared answers or evidence extracts are bundled in the code archive.
Run diagnostics under `evaluation/` identify unresolved proof gaps and retain evidence provenance for debugging.

## Architecture

1. **Authorization:** a locally trained character n-gram TF-IDF/logistic-regression classifier plus explicit refusal and deletion-intent guards. Training sentences are participant-authored in `code/intent.py`; they contain no dataset case IDs or output labels. Access, correction, export, and marketing-only requests must not authorize account deletion.
2. **Identity resolution:** current snapshots and time-filtered audit history provide exact email, phone, stable user reference, and email-hash links. Historical email hashes are reconstructed with SHA-256. Similar names or email substrings do not establish identity.
3. **Extraction:** JSON snapshots, isolated in-memory SQLite imports, multiple log dialects, plain text, PDF extraction, and local Tesseract OCR become normalized observations. Interleaved log events join by service and trace ID. Screenshot table bystanders do not become owners of the selected resource.
4. **Temporal reconstruction:** both manifest capture time and internal observation time must be at or before `audit_at`. Compare all relevant primary and replica rows. A surviving copy wins over an absent primary at the same observation time. Workflow results alone are not state evidence.
5. **Policy and planning:** apply `deletion_rules.csv`. Preserve retained security records and stable tombstone references. Stop active flows and block unsafe restores before record changes. Serialize findings, remediation, then verification using the operation/system/resource ordering specified in the challenge.
6. **Validation:** check exact columns, request coverage, unique sorted case IDs, step fields, numbering, permitted operations/states, and evidence cutoffs. COMPLETE verification cites existing evidence; proposed future work uses empty evidence IDs.

## Evaluation

[The provenance review](evaluation/provenance_review.md) traces every remaining missing sample verification to the parsed source evidence and its availability time. Diagnostics also include `ownership_links` and `unverified_resources`, separating known ownership from proven state.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python code/evaluation/main.py
```

The evaluator reads only public sample answers and participant-authored regression cases.
It writes the required Markdown report directly to `evaluation/evaluation_report.md`.
Prediction code does not read `sample_output.csv`. Hidden evaluation accuracy is unknown.
The usage report at `evaluation/usage_report.md` describes the final full-dataset run that produced the root output, including its SHA-256.

Some readbacks have no subject identifier or recoverable explicit ownership link. The auditor does not guess these links from numeric ID suffixes, case ordering, fixed timing offsets, or golden labels.
Where evidence cannot prove the required account state, the fixed schema is conservatively filled with INCOMPLETE and the reason is recorded in diagnostics. That represents insufficient proof, not necessarily a demonstrated deletion failure. Consequently, some output sequences are incomplete and the baseline should be improved before relying on its verdicts.
The supplied output contract has no UNKNOWN operation/status or retained-record restoration operation; these gaps are documented rather than hidden.

## Submission artifacts

- `code.zip`: runnable code, requirements, README, tests, and both evaluation Markdown reports.
- `output.csv`: 518 predictions.
- `log.txt`: development conversation summaries for the chat transcript slot.
- AI interview: explain evidence retrieval, identity resolution, time filtering, policy, evaluation, and remaining limitations.

Package locally with:

```bash
.venv/bin/python code/package.py
```

The packaging script uses an explicit allowlist. It excludes `dataset/`, OCR caches, virtual environments, raw diagnostics, credentials, nested archives, and the prediction CSV, which is submitted separately.
Do not claim public-sample accuracy is accuracy on the hidden 518 answers.
For optional full raw harness traces, follow `agent_trace_instructions.md` after the session ends and review/redact those files before sharing; they are not included automatically.

Challenge and submission URL:
https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists
