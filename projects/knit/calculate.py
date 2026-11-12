"""KT-1 planning estimates, not measurements. Run with Python 3; no dependencies.

Based on the user-supplied HTML's `calc()` (three-budget calculator).
Prices: https://openrouter.ai/xiaomi/mimo-v2.6-pro, checked 2026-10-04.
The original tier/quality scores are illustrative, not model benchmarks.
"""

import json

MODEL = "xiaomi/mimo-v2.6-pro"
PRICE_IN = 0.435  # USD / million tokens; conservative Xiaomi route price
PRICE_OUT = 0.87
PRICE_CACHE = 0.0036
RETRY_FACTOR = 1.20  # planning allowance, not measured retry rate
PAYMENT_FX_FACTOR = 1.10  # allowance, not a quoted provider fee
PROFILES = {
    "Q": {"tin": 6000, "tout": 600, "steps": 1, "share": 0.70},
    "U": {"tin": 8000, "tout": 1000, "steps": 3, "share": 0.25},
    "R": {"tin": 12000, "tout": 1600, "steps": 6, "share": 0.05},
}


def estimate(profile, reasoning_per_call=1000, cache_share=0.0):
    tin, tout, steps = (profile[k] for k in ("tin", "tout", "steps"))
    # Original HTML's simplified token growth (not cumulative full transcripts).
    input_tokens = tin * steps + 150 * (steps - 1)
    visible_tokens = tout + 150 * (steps - 1)
    output_tokens = visible_tokens + reasoning_per_call * steps
    original_html_cost = (input_tokens * PRICE_IN + visible_tokens * PRICE_OUT) / 1e6
    price_in = (1 - cache_share) * PRICE_IN + cache_share * PRICE_CACHE
    cost = (input_tokens * price_in + output_tokens * PRICE_OUT) / 1e6
    # HTML tier m has price multiplier 1; latency constants remain illustrative.
    original_html_latency = (
        150 + steps * 60 * (tin / 1000)
        + visible_tokens * 10 + (steps - 1) * 500
    ) / 1000
    latency = 0.8 + steps * 3 + output_tokens / 30 + (steps - 1) * 1
    return {
        "input_tokens": input_tokens,
        "visible_tokens": visible_tokens,
        "reasoning_tokens": reasoning_per_call * steps,
        "output_tokens": output_tokens,
        "html_cost_usd_without_reasoning": original_html_cost,
        "html_latency_seconds_illustrative": original_html_latency,
        "model_cost_usd": cost,
        "model_cost_with_reserves_usd": cost * RETRY_FACTOR * PAYMENT_FX_FACTOR,
        "latency_seconds_planning_only": latency,
    }


def report():
    profiles = {name: estimate(p) for name, p in PROFILES.items()}
    mean_cost = sum(PROFILES[n]["share"] * p["model_cost_usd"] for n, p in profiles.items())
    mean_seconds = sum(PROFILES[n]["share"] * p["latency_seconds_planning_only"] for n, p in profiles.items())
    monthly = {}
    for name, users, infra, development, labor in (
        ("pilot", 20, 60, 20, 900), ("startup", 100, 150, 50, 1800)
    ):
        requests = users * 20 * 10
        production = mean_cost * requests * RETRY_FACTOR * PAYMENT_FX_FACTOR
        cash = production + infra + development
        monthly[name] = {
            "users": users, "requests": requests,
            "production_model_usd": production,
            "infra_usd": infra, "development_eval_usd": development,
            "cash_total_usd": cash, "labor_opportunity_usd": labor,
            "economic_total_usd": cash + labor,
            "cash_usd_per_request": cash / requests,
            "inflight_at_business_hour_average": requests / (20 * 8 * 3600) * mean_seconds,
            "revenue_at_10_usd_subscription_plus_model_passthrough": users * 10 + production,
            "cash_surplus_before_labor_usd": users * 10 - infra - development,
        }
    return {
        "model": MODEL, "as_of": "2026-10-04", "profiles": profiles,
        "weighted_model_usd": mean_cost,
        "weighted_model_usd_with_reserves": mean_cost * RETRY_FACTOR * PAYMENT_FX_FACTOR,
        "monthly": monthly,
        "cache_50_percent_model_usd": {n: estimate(p, cache_share=0.5)["model_cost_usd"] for n, p in PROFILES.items()},
        "reasoning_3000_per_call_model_usd": {n: estimate(p, reasoning_per_call=3000)["model_cost_usd"] for n, p in PROFILES.items()},
        "eval_20_cases_5_runs_usd_at_production_mix": 20 * 5 * mean_cost,
    }


if __name__ == "__main__":
    print(json.dumps(report(), ensure_ascii=False, indent=2))
