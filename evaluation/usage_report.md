# Token usage and cost report

## Final full-dataset run

- Timestamp (UTC): 2026-10-25T08:39:59.503924+00:00
- Command: `.venv/bin/python code/main.py --cache .cache/final-run-ocr`
- Requests: **518**
- Evidence files parsed: 94
- Normalized observations: 2905
- Wall time inside the pipeline: 10.302 seconds (excludes Python import startup).
- Cache: empty OCR cache at run start; all 11 screenshots recognized locally.
- Python: 3.14.6; Tesseract: 5.5.3 (installed English recognition model).
- Python package versions: scikit-learn 1.9.1, pypdf 6.21.2, pytesseract 0.3.13, Pillow 13.0.0.
- Output: root `output.csv`, SHA-256 `9427411618d622e1f46747a123ab70857276d572fa02c76dac618b0b4023872f`.

## Models, calls, tokens, and cost

| Provider / execution | Model | Calls | Input LLM tokens | Output LLM tokens | Estimated API cost |
| --- | --- | ---: | ---: | ---: | ---: |
| Local scikit-learn | local-char-tfidf-logistic-regression-v1 | 518 | N/A (0 billed) | N/A (0 billed) | $0.00 |
| Local Tesseract | Tesseract 5.5.3 English OCR (`eng.traineddata`) | 11 | N/A (0 billed) | N/A (0 billed) | $0.00 |
| Hosted providers | None | 0 | 0 | 0 | $0.00 |
| Overall | Local text classification + OCR | 529 | 0 billed | 0 billed | **$0.00** |

Total hosted input tokens: **0**. Total hosted output tokens: **0**.
Total billed tokens: **0**; average billed tokens per request: **0 / 518 = 0**.
Estimated total API cost: **$0.00**; average API cost per request: **$0.00 / 518 = $0.00**.
The classifier receives 518 text requests and uses character n-gram features; it does not have an LLM token accounting interface.
OCR receives 11 raster images. Its internal symbols are not presented as provider tokens.
Local CPU time, electricity, and development-assistant usage are excluded from API cost, rather than incorrectly claimed to have no resource cost.
Development-assistant token counts were not supplied by the harness and are not invented here; this report covers the submitted pipeline's final run.

## Output distribution and limitations

- COMPLETE: 52
- INCOMPLETE: 456
- NOT_APPLICABLE: 10
- Cases with explicit unresolved-proof diagnostics: **342**.

These are predicted statuses, not hidden-ground-truth counts. See `evaluation_report.md` for measured public-sample accuracy and the limitations of conservative missing-proof handling.
The separate sample evaluation and regression-test runs are not included in the final 518-request call totals.
