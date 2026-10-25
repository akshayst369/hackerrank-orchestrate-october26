# Token usage and cost report

## Final full-dataset run

- Command: `.venv/bin/python code/main.py`
- Timestamp (UTC): 2026-10-25T09:24:36.691499+00:00
- Requests: 518; evidence files: 94; normalized observations: 2905.
- Pipeline wall time: 1.173 seconds, excluding Python import startup.
- OCR cache: warm; all 11 screenshot text extractions reused by image content hash. No OCR inference calls in this final run. Earlier cold-run OCR calls are not included in this run's totals.
- Python: 3.14.6; scikit-learn: 1.9.1; Tesseract installed version: 5.5.3.
- Root `output.csv` SHA-256: `31d2d2a24cfc809a29d64f1dc59386e97e4e8d2bef6099fae73b3080fe1a3716`.

## Per-model and overall totals

| Provider / execution | Model | Calls | Input tokens | Output tokens | API cost |
| --- | --- | ---: | --- | --- | ---: |
| Local scikit-learn | local-char-tfidf-logistic-regression-v1 | 518 | N/A; 0 billed | N/A; 0 billed | $0.00 |
| Local Tesseract | Tesseract 5.5.3 English OCR (`eng.traineddata`), cached | 0 | N/A; 0 billed | N/A; 0 billed | $0.00 |
| Hosted providers | None | 0 | 0 | 0 | $0.00 |
| Overall | Local inference | 518 | 0 billed | 0 billed | **$0.00** |

Total hosted input tokens: **0**; total hosted output tokens: **0**.
Total billed tokens: **0**; average billed tokens per request: **0 / 518 = 0**.
Estimated total API cost: **$0.00**; estimated average API cost per request: **$0.00 / 518 = $0.00**.
The local classifier uses character n-gram features rather than an LLM token interface; OCR uses raster inputs. Neither is misreported as generating LLM tokens.
Local CPU/electricity and development-assistant resource usage are excluded from API cost. Development-assistant token counts were not supplied by the harness and are not invented.
Separate sample evaluation, regression tests, earlier runs, and archive smoke tests are not part of the final 518-request inference totals.

## Output distribution and limitations

| Predicted status | Requests |
| --- | ---: |
| COMPLETE | 52 |
| INCOMPLETE | 456 |
| NOT_APPLICABLE | 10 |

Cases with unresolved-proof diagnostics: **342**.
These are predicted counts, not hidden truth. See `evaluation_report.md` for sample accuracy and `provenance_review.md` for missing verification evidence.
