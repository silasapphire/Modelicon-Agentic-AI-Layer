"""Deterministic content-scope guardrail.

Domain/coordinator prompts previously asked the LLM to "ignore" fields
like the power-draw lookup table or the historical trend unless the user
asked about energy or trends -- a negative instruction the small local
model followed unreliably (e.g. reporting power consumption on a plain
temperature question). The reliable fix is to not show the model those
fields at all unless the request actually calls for them: it can't
narrate data it never received.

This module decides, from the raw request text, which extra topics are
in scope, and strips everything else out of a *copy* of the data used to
build a prompt. It never touches the state dict itself -- callers keep
the full, unfiltered readings for their own return value / downstream
agents; only what gets stringified into an LLM prompt is filtered.
"""

from __future__ import annotations

ENERGY_KEYWORDS = (
    "energy", "power", "efficien", "consum", "draw", "watt",
    "save", "saving", "optimi",
)
TREND_KEYWORDS = (
    "trend", "history", "historical", "over time", "rising", "falling",
    "24h", "24 hour", "24-hour",
)

#: Field names stripped out of the prompt payload unless the request
#: mentions energy/power.
ENERGY_FIELDS = {
    "lookup_table_c_to_kw", "best_setpoint_c", "best_setpoint_power_kw", "power_kw",
    "electricity_price_inr_kwh", "energy_cost_rate_inr_h",
}
#: Field names stripped out of the prompt payload unless the request
#: mentions trends/history.
TREND_FIELDS = {"history", "timeseries", "last_24h_avg", "trend"}


def wants_energy_info(request: str) -> bool:
    text = request.lower()
    return any(kw in text for kw in ENERGY_KEYWORDS)


def wants_trend_info(request: str) -> bool:
    text = request.lower()
    return any(kw in text for kw in TREND_KEYWORDS)


def _strip(value, drop_keys: set[str]):
    if isinstance(value, dict):
        return {k: _strip(v, drop_keys) for k, v in value.items() if k not in drop_keys}
    if isinstance(value, list):
        return [_strip(v, drop_keys) for v in value]
    return value


def filter_for_prompt(data: dict, request: str) -> dict:
    """Return a copy of ``data`` with energy/trend fields removed unless
    the request actually asked about them, so a prompt built from the
    result can't narrate details nobody asked for."""
    drop_keys: set[str] = set()
    if not wants_energy_info(request):
        drop_keys |= ENERGY_FIELDS
    if not wants_trend_info(request):
        drop_keys |= TREND_FIELDS
    return _strip(data, drop_keys)
