# LiteLLM model optimizer

`litellm_model_optimizer.py` queries the internal LiteLLM `/models` endpoint, downloads the current LiteLLM pricing catalog, and reads the public DeepSWE, Artificial Analysis Coding Agent, and SWE-bench leaderboards. It prints terminal-friendly ranked tables with separate paid/provider-priced and self-hosted/unpriced sections, and can optionally write a CSV suitable for spreadsheets.

## Run

```sh
export GEN_LLLM_CLAUDE_KEY='your-key'
python3 litellm_model_optimizer.py
```

By default the ranking is printed only to the terminal. Use `--csv rankings.csv` when a spreadsheet export is needed. Use `--limit 20` to print only the top 20 models.

The key is sent only as the `x-litellm-api-key` header to the LiteLLM endpoint. It is not written to either output file.

## Scoring

Each source score is converted to a fraction if it is reported as a percentage. Scores are already on a common 0–1 scale, so no dataset-dependent min–max transformation is applied. For sources with multiple configurations, the best published score for each model is used. A model's `intelligence_index` is the maximum of its available source scores. Missing source scores are ignored; if no source matches, the intelligence score is left blank. `value_score` is the intelligence index divided by the mean of LiteLLM's input and output price per million tokens. Paid models sort by value score, then intelligence, then cost. Models missing public pricing are classified as self-hosted/unpriced and sort by intelligence.

The script has dedicated parsers for the current embedded formats: DeepSWE serialized `model`/`pass_rate` records, Artificial Analysis `hostModelSlug`/`indexScore` records, and SWE-bench's embedded `leaderboard-data` JSON. The terminal output records `scores_found` and a source status so an empty parser result is visible rather than silently treated as a real zero. To supplement or override parsed leaderboard values, provide a JSON file:

```json
{
  "deep_swe": {"claude-sonnet-4": 72},
  "artificial_analysis": {"claude-sonnet-4": 0.81},
  "swe_bench": {"claude-sonnet-4": 55}
}
```

```sh
python3 litellm_model_optimizer.py --scores-file scores.json
```

A source URL can be overridden without editing the script:

```sh
python3 litellm_model_optimizer.py \
  --source-url artificial_analysis=https://example.internal/export.json
```
