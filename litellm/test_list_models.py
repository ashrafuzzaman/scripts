import unittest

from list_models import _build_rows, match_swe_bench_score


class MatchSweBenchScoreTests(unittest.TestCase):
    def test_matches_provider_prefixed_name_with_reordered_tokens(self) -> None:
        self.assertEqual(
            match_swe_bench_score(
                "anthropic/claude-sonnet-4",
                {"claude-4-sonnet": 0.71},
            ),
            0.71,
        )

    def test_matches_dated_model_alias(self) -> None:
        self.assertEqual(
            match_swe_bench_score(
                "openai/gpt-4o-2024-08-06",
                {"gpt-4o": 0.62},
            ),
            0.62,
        )

    def test_does_not_match_different_models(self) -> None:
        self.assertIsNone(
            match_swe_bench_score(
                "openai/gpt-4o",
                {"claude-3-5-haiku": 0.44},
            )
        )

    def test_rows_only_include_requested_columns(self) -> None:
        rows = _build_rows(
            [{"id": "anthropic/claude-sonnet-4", "owned_by": "anthropic", "mode": "chat"}],
            {"claude-4-sonnet": 0.71},
        )
        self.assertEqual(
            rows,
            [{
                "provider": "Anthropic",
                "id": "anthropic/claude-sonnet-4",
                "owned_by": "anthropic",
                "mode": "chat",
                "input ($/1M)": "-",
                "output ($/1M)": "-",
                "cache read ($/1M)": "-",
                "cache write ($/1M)": "-",
                "SWE-bench": "71.0%",
            }],
        )

    def test_filters_do_not_use_ids_and_empty_modes(self) -> None:
        rows = _build_rows(
            [
                {"id": "openai/gpt-4o-do_not_use", "mode": "chat"},
                {"id": "anthropic/claude-no-mode", "mode": ""},
                {"id": "gemini/empty-mode", "mode": "   "},
                {"id": "openai/gpt-4o", "mode": " chat "},
            ],
            {},
        )
        self.assertEqual([row["id"] for row in rows], ["openai/gpt-4o"])
        self.assertEqual(rows[0]["mode"], "chat")

    def test_costs_are_per_million_tokens_and_include_cache_rates(self) -> None:
        rows = _build_rows(
            [{"id": "anthropic/claude-sonnet-4", "mode": "chat"}],
            {},
            {
                "claude-sonnet-4": {
                    "input_cost_per_token": 0.000003,
                    "output_cost_per_token": 0.000015,
                    "cache_read_input_token_cost": 0.0000003,
                    "cache_creation_input_token_cost": 0.00000375,
                }
            },
        )
        self.assertEqual(rows[0]["input ($/1M)"], "$3.0000")
        self.assertEqual(rows[0]["output ($/1M)"], "$15.0000")
        self.assertEqual(rows[0]["cache read ($/1M)"], "$0.3000")
        self.assertEqual(rows[0]["cache write ($/1M)"], "$3.7500")

    def test_rows_are_grouped_in_provider_order(self) -> None:
        rows = _build_rows(
            [
                {"id": "gemini/gemini-2.5-pro", "owned_by": "google", "mode": "chat"},
                {"id": "openai/gpt-4o", "owned_by": "openai", "mode": "chat"},
                {"id": "custom/model", "owned_by": "internal", "mode": "chat"},
                {"id": "anthropic/claude-sonnet-4", "owned_by": "anthropic", "mode": "chat"},
            ],
            {},
        )
        self.assertEqual(
            [row["provider"] for row in rows],
            ["Anthropic", "OpenAI", "Gemini", "Other"],
        )


if __name__ == "__main__":
    unittest.main()
