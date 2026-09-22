#!/usr/bin/env python3
"""Rank LiteLLM models by coding intelligence per dollar.

The script intentionally uses only Python's standard library. It fetches:
  * models from the configured LiteLLM /models endpoint;
  * current pricing from LiteLLM's model_prices_and_context_window.json;
  * public DeepSWE, Artificial Analysis, and SWE-bench leaderboards.

Leaderboard pages change format occasionally. Use --scores-file to supplement
or replace parsed scores with a JSON object such as:
{
  "deep_swe": {"claude-sonnet-4": 0.72},
  "artificial_analysis": {"claude-sonnet-4": 0.81},
  "swe_bench": {"claude-sonnet-4": 0.55}
}
Scores may be percentages (72) or fractions (0.72).
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

LITELLM_MODELS_URL = (
    "https://litellm.prod.aws.lifelock.com/models?"
    "return_wildcard_routes=false&include_model_access_groups=false&"
    "only_model_access_groups=false&include_metadata=false"
)
PRICES_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
SOURCES = {
    "deep_swe": "https://deepswe.datacurve.ai/",
    "artificial_analysis": "https://artificialanalysis.ai/agents/coding-agents",
    "swe_bench": "https://www.swebench.com/",
}


def fetch(url: str, api_key: str | None = None, timeout: int = 30) -> bytes:
    headers = {"User-Agent": "litellm-model-optimizer/1.0", "Accept": "application/json,text/html"}
    if api_key:
        headers["x-litellm-api-key"] = api_key
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def load_json_url(url: str, api_key: str | None = None) -> Any:
    return json.loads(fetch(url, api_key).decode("utf-8-sig"))


def plain_text(raw: bytes) -> str:
    value = raw.decode("utf-8", "ignore")
    value = re.sub(r"<(script|style|noscript)\b[^>]*>.*?</\1>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def canonical(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"^(openai|anthropic|google|vertex_ai|azure|bedrock|gemini|hosted_vllm|deepseek|mistral)[/_]", "", name)
    name = re.sub(r"^(litellm_proxy[/_]|models[/_])", "", name)
    name = re.sub(r"\[[^]]+\]|\([^)]*\)", "", name)
    name = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return name


def score(value: str) -> float:
    number = float(value.rstrip("%"))
    return number / 100 if number > 1 else number


def _best_values(values: dict[str, list[float]]) -> dict[str, float]:
    """Use the best published configuration for each model.

    DeepSWE publishes multiple reasoning-effort configurations per model. A
    model score should not be diluted by averaging in intentionally weaker
    configurations.
    """
    return {key: max(items) for key, items in values.items() if items}


def parse_scores(raw: bytes, source: str) -> dict[str, float]:
    """Parse the published data formats used by each benchmark page."""
    text = raw.decode("utf-8", "ignore")
    values: dict[str, list[float]] = {}
    if source == "deep_swe":
        # DeepSWE's RSC payload contains one record per effort level.
        matches = re.finditer(r'model:\"([^\"]+)\".{0,2500}?pass_rate:([0-9.]+)', text)
        for match in matches:
            values.setdefault(canonical(match.group(1)), []).append(float(match.group(2)))
        return _best_values(values)
    if source == "artificial_analysis":
        # Artificial Analysis serializes the current index as escaped RSC JSON.
        matches = re.finditer(r'hostModelSlug\\":\\"([^\"]+)\\".{0,12000}?indexScore\\":([0-9.]+)', text)
        for match in matches:
            values.setdefault(canonical(match.group(1)), []).append(float(match.group(2)))
        return _best_values(values)
    if source == "swe_bench":
        match = re.search(r'<script type="application/json" id="leaderboard-data">(.*?)</script>', text, flags=re.DOTALL)
        if match:
            try:
                leaderboards = json.loads(match.group(1))
            except json.JSONDecodeError:
                leaderboards = []
            for leaderboard in leaderboards:
                for result in leaderboard.get("results", []):
                    resolved = result.get("resolved")
                    if not isinstance(resolved, (int, float)):
                        continue
                    model = next((tag[6:] for tag in result.get("tags", []) if isinstance(tag, str) and tag.lower().startswith("model:")), None)
                    model = model or result.get("model_display") or result.get("name")
                    if model:
                        values.setdefault(canonical(model), []).append(float(resolved) / 100)
            return _best_values(values)
    # Fallback for a simple visible/JSON percentage table.
    visible = plain_text(raw)
    patterns = [
        r"([A-Za-z][A-Za-z0-9_.:/-]{2,})\s*\[[^\]]+\]\s*(\d+(?:\.\d+)?)%",
        r"([A-Za-z][A-Za-z0-9_.:/-]{2,})\s+(\d+(?:\.\d+)?)%",
        r'"(?:model|name|model_name)"\s*:\s*"([^"]+)"[^{}]{0,500}?"(?:score|index|pass_at_1|resolved)"\s*:\s*(\d+(?:\.\d+)?)',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, visible, flags=re.IGNORECASE):
            key = canonical(match.group(1))
            if key and key not in {"models", "model", "score", "index"}:
                values.setdefault(key, []).append(score(match.group(2)))
    return _best_values(values)


def read_scores_file(path: str | None) -> dict[str, dict[str, float]]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {source: {canonical(k): score(str(v)) for k, v in values.items()} for source, values in data.items()}


def model_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("data", "models", "model_list"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise TypeError("LiteLLM /models response is not a list or {data: list}")
    result = []
    for item in payload:
        if isinstance(item, str):
            result.append({"model_name": item})
        elif isinstance(item, dict):
            name = item.get("model_name") or item.get("model") or item.get("id")
            if name:
                result.append(item)
    return result


def price_for(name: str, prices: dict[str, Any]) -> tuple[float | None, float | None, str | None]:
    candidates = [name, name.removeprefix("openai/"), name.removeprefix("anthropic/")]
    key = next((candidate for candidate in candidates if candidate in prices), None)
    if key is None:
        ck = canonical(name)
        key = next((k for k in prices if canonical(k) == ck), None)
    if key is None:
        return None, None, None
    item = prices[key] if isinstance(prices[key], dict) else {}
    return item.get("input_cost_per_token"), item.get("output_cost_per_token"), key


def aliases(name: str) -> set[str]:
    base = canonical(name)
    values = {base}
    # Providers commonly expose dated or deployment-prefixed names.
    values.add(re.sub(r"-\d{4}-\d{2}-\d{2}$", "", base))
    values.add(re.sub(r"-(?:latest|preview)$", "", base))
    return values


def normalized_scores(scores: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Return benchmark scores already normalized to the common [0, 1] scale.

    Percentages are converted while parsing. Min-max normalization is not used:
    it makes a model's score depend on which other models happen to be listed.
    """
    return {source: {key: max(0.0, min(1.0, value)) for key, value in values.items()} for source, values in scores.items()}


def rank(models: list[dict[str, Any]], prices: dict[str, Any], scores: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    scores = normalized_scores(scores)
    output = []
    for item in models:
        name = str(item.get("model_name") or item.get("model") or item.get("id"))
        in_cost, out_cost, price_key = price_for(name, prices)
        matched: dict[str, float] = {}
        for source, values in scores.items():
            candidates = [values[k] for alias in aliases(name) for k in values if alias == canonical(k)]
            if candidates:
                matched[source] = candidates[0]
        # Always use the strongest available intelligence result for a model.
        intelligence = max(matched.values()) if matched else None
        # Cost is USD per million tokens. If pricing is absent, rank at the end.
        blended_cost = None if in_cost is None or out_cost is None else (in_cost + out_cost) / 2 * 1_000_000
        efficiency = None if intelligence is None or blended_cost in (None, 0) else intelligence / blended_cost
        output.append({
            "model": name,
            "deployment": "self-hosted/unpriced" if blended_cost is None or blended_cost <= 0 else "paid/provider-priced",
            "intelligence_index": intelligence,
            "intelligence_sources": matched,
            "source_count": len(matched),
            "input_cost_usd_per_1m_tokens": None if in_cost is None else in_cost * 1_000_000,
            "output_cost_usd_per_1m_tokens": None if out_cost is None else out_cost * 1_000_000,
            "average_cost_usd_per_1m_tokens": blended_cost,
            "litellm_price_key": price_key,
            "value_score": efficiency,
        })
    return output


def print_table(rows: list[dict[str, Any]], source_status: dict[str, Any]) -> None:
    print("LiteLLM coding model optimizer")
    print("=" * 100)
    print("Intelligence = maximum available published source score on a 0-1 scale.")
    print("Value = intelligence / average input-output cost per 1M tokens. Higher is better.\n")
    print("Sources:")
    for source, status in source_status.items():
        print(f"  {source:<20} {status['scores_found']:>4} scores  {status['status']}")
    print()
    headers = ("#", "Model", "Intel", "Sources", "Avg $/1M", "Value")

    def display_section(title: str, section_rows: list[dict[str, Any]]) -> None:
        print(title)
        print("-" * len(title))
        table_rows = []
        for index, row in enumerate(section_rows, 1):
            table_rows.append((
                str(index),
                row["model"],
                "-" if row["intelligence_index"] is None else f"{row['intelligence_index']:.3f}",
                str(row["source_count"]),
                "-" if row["average_cost_usd_per_1m_tokens"] is None else f"${row['average_cost_usd_per_1m_tokens']:.4f}",
                "-" if row["value_score"] is None else f"{row['value_score']:.5f}",
            ))
        widths = [len(headers[index]) for index in range(len(headers))]
        for row in table_rows:
            for index, value in enumerate(row):
                widths[index] = min(max(widths[index], len(value)), 60)
        def render(row: tuple[str, ...]) -> str:
            cells = []
            for index, value in enumerate(row):
                value = value if len(value) <= widths[index] else value[: widths[index] - 1] + "…"
                cells.append(value.rjust(widths[index]) if index in {0, 2, 3, 4, 5} else value.ljust(widths[index]))
            return "  ".join(cells)
        print(render(headers))
        print("  ".join("-" * width for width in widths))
        for row in table_rows:
            print(render(row))
        print()

    paid = [row for row in rows if row["deployment"] == "paid/provider-priced"]
    self_hosted = [row for row in rows if row["deployment"] == "self-hosted/unpriced"]
    # Paid models prioritize value, then intelligence and lower cost. Unpriced
    # models cannot have a value score, so prioritize intelligence then cost.
    paid.sort(key=lambda row: (row["value_score"] is None, -(row["value_score"] or 0), -(row["intelligence_index"] or 0), row["average_cost_usd_per_1m_tokens"] or float("inf")))
    self_hosted.sort(key=lambda row: (row["intelligence_index"] is None, -(row["intelligence_index"] or 0), row["model"]))
    display_section("PAID / PROVIDER-PRICED MODELS", paid)
    display_section("SELF-HOSTED / UNPRICED MODELS", self_hosted)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", dest="csv_path", help="Optional CSV output path")
    parser.add_argument("--limit", type=int, help="Only print the top N ranked models")
    parser.add_argument("--scores-file", help="Optional JSON file with manually supplied leaderboard scores")
    parser.add_argument("--source-url", action="append", metavar="NAME=URL", help="Override a leaderboard URL")
    args = parser.parse_args()
    key = os.environ.get("GEN_LLLM_CLAUDE_KEY")
    if not key:
        print("GEN_LLLM_CLAUDE_KEY is required", file=sys.stderr)
        return 2
    urls = dict(SOURCES)
    for override in args.source_url or []:
        name, separator, url = override.partition("=")
        if not separator or name not in urls:
            parser.error("--source-url must be NAME=URL for deep_swe, artificial_analysis, or swe_bench")
        urls[name] = url
    try:
        models = model_entries(load_json_url(LITELLM_MODELS_URL, key))
        prices = load_json_url(PRICES_URL)
    except Exception as exc:
        print(f"Unable to fetch LiteLLM models/pricing: {exc}", file=sys.stderr)
        return 1
    parsed_scores: dict[str, dict[str, float]] = {}
    source_status = {}
    for source, url in urls.items():
        try:
            parsed = parse_scores(fetch(url), source)
            parsed_scores[source] = parsed
            source_status[source] = {"url": url, "scores_found": len(parsed), "status": "ok"}
        except Exception as exc:
            parsed_scores[source] = {}
            source_status[source] = {"url": url, "scores_found": 0, "status": f"unavailable: {exc}"}
    scores = parsed_scores
    for source, overrides in read_scores_file(args.scores_file).items():
        scores.setdefault(source, {}).update(overrides)
    rows = rank(models, prices, scores)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero")
    print_table(rows if args.limit is None else rows[:args.limit], source_status)
    if args.csv_path:
        fields = ["model", "intelligence_index", "source_count", "average_cost_usd_per_1m_tokens", "value_score", "input_cost_usd_per_1m_tokens", "output_cost_usd_per_1m_tokens"]
        with Path(args.csv_path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows({field: row[field] for field in fields} for row in rows)
        print(f"\nCSV written to {args.csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
