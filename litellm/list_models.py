#!/usr/bin/env python3
"""List configured LiteLLM model names, pricing, and SWE-bench scores."""
from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from litellm_model_optimizer import PRICES_URL, canonical, model_entries, parse_scores, price_for

SWE_BENCH_URL = "https://www.swebench.com/"
USER_AGENT = "litellm-model-list/1.0"
MIN_FUZZY_SIMILARITY = 0.84
AMBIGUITY_GAP = 0.035


def _model_aliases(name: str) -> set[str]:
    base = canonical(name)
    aliases = {base}
    aliases.add(re.sub(r"-(?:\d{4}-\d{2}-\d{2}|\d{8})$", "", base))
    aliases.add(re.sub(r"-(?:latest|preview|stable)$", "", base))
    return {alias for alias in aliases if alias}


def _similarity(left: str, right: str) -> float:
    direct = difflib.SequenceMatcher(None, left, right).ratio()
    left_tokens = " ".join(sorted(set(left.split("-"))))
    right_tokens = " ".join(sorted(set(right.split("-"))))
    reordered = difflib.SequenceMatcher(None, left_tokens, right_tokens).ratio()
    return max(direct, reordered)


def match_swe_bench_score(
    model_name: str,
    scores: dict[str, float],
    *,
    minimum_similarity: float = MIN_FUZZY_SIMILARITY,
    ambiguity_gap: float = AMBIGUITY_GAP,
) -> float | None:
    """Match a LiteLLM model to SWE-bench, rejecting weak or ambiguous matches."""
    model_aliases = _model_aliases(model_name)
    exact_matches: list[float] = []
    candidates: list[tuple[float, str, float]] = []

    for benchmark_name, benchmark_score in scores.items():
        benchmark_aliases = _model_aliases(benchmark_name)
        if model_aliases & benchmark_aliases:
            exact_matches.append(benchmark_score)
            continue

        similarity = max(
            _similarity(model_alias, benchmark_alias)
            for model_alias in model_aliases
            for benchmark_alias in benchmark_aliases
        )
        # Different numeric/version tokens usually mean a different model (for
        # example, Claude 4 vs Claude 4.1), not a harmless naming variation.
        model_versions = {tuple(re.findall(r"\d+", alias)) for alias in model_aliases}
        benchmark_versions = {tuple(re.findall(r"\d+", alias)) for alias in benchmark_aliases}
        if not model_versions.intersection(benchmark_versions):
            continue
        candidates.append((similarity, benchmark_name, benchmark_score))

    if exact_matches:
        return max(exact_matches)

    candidates.sort(key=lambda candidate: (-candidate[0], candidate[1]))
    if not candidates or candidates[0][0] < minimum_similarity:
        return None
    if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < ambiguity_gap:
        return None
    return candidates[0][2]


def _cache_metadata_path(cache_path: Path) -> Path:
    return cache_path.with_suffix(cache_path.suffix + ".http.json")


def _read_metadata(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", dir=path.parent, delete=False
        ) as handle:
            temporary_path = handle.name
            handle.write(content)
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _cache_control(cache_control: str) -> dict[str, str | None]:
    directives: dict[str, str | None] = {}
    for directive in cache_control.split(","):
        name, separator, value = directive.strip().partition("=")
        if name:
            directives[name.lower()] = value.strip().strip('"') if separator else None
    return directives


def fetch_cached(url: str, cache_path: Path, source_name: str = "resource") -> bytes:
    """Fetch with HTTP validators and Cache-Control freshness when available."""
    metadata_path = _cache_metadata_path(cache_path)
    metadata = _read_metadata(metadata_path)
    has_cache = cache_path.is_file() and metadata.get("url") == url
    cached_body = cache_path.read_bytes() if has_cache else None
    cached_control = _cache_control(str(metadata.get("cache_control", "")))

    if has_cache and "no-cache" not in cached_control:
        max_age = cached_control.get("max-age")
        if max_age is not None:
            try:
                age = time.time() - float(metadata.get("stored_at", 0))
                if age < max(0, int(max_age)):
                    return cached_body or b""
            except (TypeError, ValueError):
                pass

    headers = {
        "Accept": "text/html,application/json",
        "User-Agent": USER_AGENT,
    }
    if has_cache:
        if metadata.get("etag"):
            headers["If-None-Match"] = str(metadata["etag"])
        if metadata.get("last_modified"):
            headers["If-Modified-Since"] = str(metadata["last_modified"])

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
            response_headers = response.headers
    except HTTPError as exc:
        if exc.code == 304 and cached_body is not None:
            response_headers = exc.headers
            cache_control = response_headers.get("Cache-Control") or metadata.get("cache_control", "")
            updated = {
                **metadata,
                "etag": response_headers.get("ETag") or metadata.get("etag"),
                "last_modified": response_headers.get("Last-Modified") or metadata.get("last_modified"),
                "cache_control": cache_control,
                "stored_at": time.time(),
            }
            if "no-store" in _cache_control(str(cache_control)):
                cache_path.unlink(missing_ok=True)
                metadata_path.unlink(missing_ok=True)
            else:
                _atomic_write(metadata_path, json.dumps(updated).encode("utf-8"))
            return cached_body
        if cached_body is not None and 500 <= exc.code < 600:
            print(f"warning: {source_name} returned HTTP {exc.code}; using its cached response", file=sys.stderr)
            return cached_body
        raise
    except (URLError, TimeoutError, OSError) as exc:
        if cached_body is not None:
            print(f"warning: {source_name} fetch failed ({exc}); using its cached response", file=sys.stderr)
            return cached_body
        raise

    cache_control = response_headers.get("Cache-Control", "")
    if "no-store" in _cache_control(cache_control):
        cache_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        return body

    new_metadata = {
        "url": url,
        "etag": response_headers.get("ETag"),
        "last_modified": response_headers.get("Last-Modified"),
        "cache_control": cache_control,
        "stored_at": time.time(),
    }
    _atomic_write(cache_path, body)
    _atomic_write(metadata_path, json.dumps(new_metadata).encode("utf-8"))
    return body


PROVIDER_ORDER = {"Anthropic": 0, "OpenAI": 1, "Gemini": 2, "Other": 3}
PROVIDER_NAMES = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "gemini": "Gemini",
}


def _provider_for(model_id: str, owned_by: Any) -> str:
    normalized_id = model_id.strip().casefold()
    namespace = normalized_id.split("/", 1)[0]
    owner = str(owned_by or "").strip().casefold().split("/", 1)[0]

    for hint in (namespace, owner):
        if hint in PROVIDER_NAMES:
            return PROVIDER_NAMES[hint]

    model_name = normalized_id.rsplit("/", 1)[-1]
    if model_name.startswith("claude-"):
        return "Anthropic"
    if re.match(r"^(?:gpt-|chatgpt-|codex-|text-embedding-|o[1-4](?:-|$))", model_name):
        return "OpenAI"
    if model_name.startswith("gemini-") or model_name == "gemini":
        return "Gemini"
    return "Other"


def _format_score(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.1f}%"


def _format_cost(value: Any) -> str:
    if value is None:
        return "-"
    try:
        cost_per_token = float(value)
    except (TypeError, ValueError):
        return "-"
    if not math.isfinite(cost_per_token) or cost_per_token < 0:
        return "-"
    return f"${cost_per_token * 1_000_000:.4f}"


def _cost_columns(model_name: str, prices: dict[str, Any]) -> dict[str, str]:
    columns = {
        "input ($/1M)": "-",
        "output ($/1M)": "-",
        "cache read ($/1M)": "-",
        "cache write ($/1M)": "-",
    }
    if not prices:
        return columns

    _, _, price_key = price_for(model_name, prices)
    price = prices.get(price_key) if price_key else None
    if not isinstance(price, dict):
        return columns

    columns["input ($/1M)"] = _format_cost(price.get("input_cost_per_token"))
    columns["output ($/1M)"] = _format_cost(price.get("output_cost_per_token"))
    columns["cache read ($/1M)"] = _format_cost(price.get("cache_read_input_token_cost"))
    columns["cache write ($/1M)"] = _format_cost(price.get("cache_creation_input_token_cost"))
    return columns


def _build_rows(
    models: list[dict[str, Any]],
    scores: dict[str, float],
    prices: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    prices = prices or {}
    rows = []
    for model in models:
        model_id = model.get("id") or model.get("model_name") or model.get("model")
        if not model_id:
            continue
        model_name = str(model_id).strip()
        if not model_name or "do_not_use" in model_name.casefold():
            continue

        mode = model.get("mode")
        if not mode or not str(mode).strip():
            continue

        owned_by = model.get("owned_by")
        score = match_swe_bench_score(model_name, scores)
        rows.append(
            {
                "provider": _provider_for(model_name, owned_by),
                "id": model_name,
                "owned_by": str(owned_by or "-"),
                "mode": str(mode).strip(),
                **_cost_columns(model_name, prices),
                "SWE-bench": _format_score(score),
            }
        )
    return sorted(
        rows,
        key=lambda row: (PROVIDER_ORDER[row["provider"]], row["id"].casefold()),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-file", required=True, type=Path)
    parser.add_argument("--cache-dir", required=True, type=Path)
    args = parser.parse_args()

    try:
        payload = json.loads(args.models_file.read_text(encoding="utf-8"))
        models = model_entries(payload)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        print(f"error: unable to read LiteLLM model response: {exc}", file=sys.stderr)
        return 1

    try:
        page = fetch_cached(SWE_BENCH_URL, args.cache_dir / "swebench.html", "SWE-bench")
        scores = parse_scores(page, "swe_bench")
    except (URLError, TimeoutError, OSError, ValueError, TypeError) as exc:
        print(f"warning: SWE-bench is unavailable; scores will be blank ({exc})", file=sys.stderr)
        scores = {}

    try:
        pricing_page = fetch_cached(PRICES_URL, args.cache_dir / "model-prices.json", "LiteLLM pricing catalog")
        prices = json.loads(pricing_page)
        if not isinstance(prices, dict):
            raise TypeError("pricing catalog response is not an object")
    except (URLError, TimeoutError, OSError, ValueError, TypeError) as exc:
        print(f"warning: LiteLLM pricing is unavailable; costs will be blank ({exc})", file=sys.stderr)
        prices = {}

    rows = _build_rows(models, scores, prices)
    if not rows:
        print("No models returned.", file=sys.stderr)
        return 0

    try:
        subprocess.run(
            ["ctp", "-i", json.dumps(rows, ensure_ascii=False, separators=(",", ":"))],
            check=True,
        )
    except FileNotFoundError:
        print("error: ctp is not installed; run litellm/setup.sh", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"error: ctp failed with exit status {exc.returncode}", file=sys.stderr)
        return exc.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
