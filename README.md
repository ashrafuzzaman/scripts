# LiteLLM model optimizer

`litellm/litellm_model_optimizer.py` queries the internal LiteLLM `/models` endpoint, downloads the current LiteLLM pricing catalog, and reads the public DeepSWE, Artificial Analysis Coding Agent, and SWE-bench leaderboards. It prints terminal-friendly ranked tables with separate paid/provider-priced and self-hosted/unpriced sections, and can optionally write a CSV suitable for spreadsheets.

Scripts are grouped by purpose: `editors/` contains editor utilities, `kubernetes/` contains the EKS helpers, and `litellm/` contains LiteLLM tools.

## Run

```sh
export GEN_LLLM_CLAUDE_KEY='your-key'
python3 litellm/litellm_model_optimizer.py
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
python3 litellm/litellm_model_optimizer.py --scores-file scores.json
```

A source URL can be overridden without editing the script:

```sh
python3 litellm/litellm_model_optimizer.py \
  --source-url artificial_analysis=https://example.internal/export.json
```

## List configured models

`litellm/models.sh` calls the internal `/models` endpoint, excludes IDs containing `do_not_use` and models without a `mode`, then groups rows by provider. Its columns include `provider`, `id` (model name), `owned_by`, `mode`, input/output costs, cache-read/cache-write costs, and `SWE-bench`; Anthropic, OpenAI, and Gemini appear first, followed by other providers. Costs are USD per 1M tokens.

```sh
./litellm/setup.sh # installs ctp with npm install --global table-printer-cli
export LITELLM_API_KEY='your-key'
./litellm/models.sh
```

The model response, SWE-bench leaderboard, and LiteLLM pricing catalog are cached under `${XDG_CACHE_HOME:-~/.cache}/litellm-model-list`. cURL uses ETag conditional requests for `/models`; the public data sources use ETag/Last-Modified validators and honor `Cache-Control` freshness. Pricing is matched by LiteLLM's model-name aliases; rates absent from the catalog display `-`. SWE-bench matching normalizes provider prefixes and dated aliases, then applies token-order-insensitive fuzzy matching; weak or ambiguous matches display `-`.

# Kubernetes (EKS) helpers

Shell versions of Confluence [HOW-TO: Setup kubectl on your local dev machine](https://moneylion.atlassian.net/wiki/spaces/IN2/pages/3535536293). They need `kubectl` and the AWS CLI. `fzf` is optional (`brew install fzf`); without it you get a numbered menu.

## Access

Raise an ITSD ticket for EKS access. For read access to MoneyLion clusters, use an AWS profile for the `staging-k8s-developer` (staging) or `production-k8s-developer` (production) SSO role. Other roles may list clusters but get `Forbidden` on pods.

## Scripts

| Script | What it does |
| --- | --- |
| `kubernetes/kube_setup.sh` | Adds a `<profile>/<cluster>` context for every EKS cluster the profile can see, same as the doc's gist but without prompts |
| `kubernetes/kube_context.sh` | Switches context by fuzzy name |
| `kubernetes/kube_pod_shell.sh` | Finds a pod by fuzzy name and opens `bash` (or `sh`) in it, or runs a command |

```sh
./kubernetes/kube_setup.sh -p staging-k8s -c stag-eks   # pull contexts, switch to stag-eks
./kubernetes/kube_context.sh prodcore                   # -> <profile>/prod-core-be

./kubernetes/kube_pod_shell.sh email-api                         # all namespaces, Running pods only
./kubernetes/kube_pod_shell.sh -x stag-eks -n staging encbf      # "encbf" matches docdb-encryption-backfill-...
./kubernetes/kube_pod_shell.sh staging backfill                  # several terms must all match
./kubernetes/kube_pod_shell.sh -a backfill                       # include Pending/Succeeded/Failed pods
./kubernetes/kube_pod_shell.sh email-api -c app -- printenv HOSTNAME
```

Matching is case-insensitive. An exact name match ranks first, then a substring of the pod name, then a substring of the namespace, then the query's characters in order. With one match it connects straight away; with several it shows a picker.

Make targets: `make kube-setup PROFILE=staging-k8s CONTEXT=stag-eks`, `make kube-context Q=stag-eks`, `make kube-shell Q=email-api CONTEXT=stag-eks NS=staging`.
