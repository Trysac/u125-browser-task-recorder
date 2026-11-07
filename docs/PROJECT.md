# Project record

## Objective

Turn recorded browser steps, including Chrome DevTools Recorder JSON exports, into reproducible Playwright Python scripts with safe literals and secrets moved to environment variables.

## Scope

The project provides a library for parsing and converting browser session recordings into clean Playwright Python scripts. It handles format parsing (Chrome DevTools and native), step normalization, and automated secret redaction using environment variables.

## Out of Scope

- Capturing events from a live browser (use DevTools Recorder or similar tools).
- Running the generated script.
- TypeScript output.
- Assertions generation.
- Waits tuning.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

| Metric | Value |
|---|---|
| Tokens (input / output) | 590952 / 13563 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.1507 |

## Factory run u125 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 4477 | 10885 | 0 | 0 | 0.0221 |
| fix-1 | gemini-3.8-flash | no | 35873 | 541 | 0 | 83626 | 0.0352 |
| fix-2 | gemini-3.8-flash | no | 32893 | 327 | 0 | 81845 | 0.0320 |
| audit | gemini-3.1-flash-lite | no | 47138 | 386 | 0 | 130500 | 0.0156 |
| docs | gemini-3.1-flash-lite | no | 174600 | 1424 | 0 | 0 | 0.0458 |

Total: $0.1507. Prices: Anthropic list prices.
