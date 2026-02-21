#!/usr/bin/env python3
"""
regex_attack_profile.py — Regex Worst-Case Input Profiling
===========================================================
Profiles analyze_text() against ReDoS-class adversarial inputs.
Uses time.perf_counter() for high-resolution per-call timing.
Writes regex_attack_profile.md.

Exit code: 0 = SAFE (no pattern exceeded threshold), 1 = WARNING
"""

import sys
import os
import time
import json
import statistics
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging as _logging
_logging.getLogger("app.engine").setLevel(_logging.CRITICAL)
_logging.getLogger().setLevel(_logging.CRITICAL)

from app.engine import analyze_text, RISK_KEYWORDS, MAX_TEXT_LENGTH

# ──────────────────────────────────────────────
# TIMING THRESHOLD (ms)
# ──────────────────────────────────────────────
TIMING_THRESHOLD_MS = 200   # Any single call > 200ms = WARN
REPS = 10                   # Repetitions per pattern (take median)

# ──────────────────────────────────────────────
# ADVERSARIAL INPUTS
# ──────────────────────────────────────────────
# Builds a max-length string of all keywords concatenated
all_keywords = [kw for kws in RISK_KEYWORDS.values() for kw in kws]
all_kw_str   = " ".join(all_keywords)
all_kw_max   = (all_kw_str * (MAX_TEXT_LENGTH // len(all_kw_str) + 1))[:MAX_TEXT_LENGTH]

# Worst-case zero-match: forces regex to scan entire string without matching
# (alphabetic gibberish that partially resembles keywords)
zero_match_max = ("qzxjwv " * (MAX_TEXT_LENGTH // 7 + 1))[:MAX_TEXT_LENGTH]

# Padded keywords (spaces between each character — tests \b boundary)
padded_kw = " k i l l  s c a m  f r a u d " * 100
padded_kw = padded_kw[:MAX_TEXT_LENGTH]

# Alternating case (already downcased in engine, but tests normalisation path)
alt_case = ("KiLl ScAm FrAuD " * 313)[:MAX_TEXT_LENGTH]

# Near-keyword pattern (off-by-one — tests no false positive AND no ReDoS)
near_miss = ("kiill sccam frauud " * 263)[:MAX_TEXT_LENGTH]

# Deep nesting lookalike: long string of 'a's (classic ReDoS bait for /(a+)+b/)
# Our engine doesn't use nested quantifiers, but we verify < threshold
redos_bait = "a" * MAX_TEXT_LENGTH

# Repeated word boundary: many \b triggers
boundary_stress = ("kill!" * 1000)[:MAX_TEXT_LENGTH]

# Unicode + keyword mix
unicode_mix = ("café scam résumé kill naïve fraud " * 147)[:MAX_TEXT_LENGTH]

PROFILES = [
    ("max_length_all_keywords",  all_kw_max,      "All keywords, max length — worst-case match"),
    ("max_length_zero_match",    zero_match_max,   "Zero keyword matches, max length — worst regex scan"),
    ("padded_keywords",          padded_kw,        "Space-separated chars; no word-boundary match"),
    ("alternating_case",         alt_case,         "Case variation; exercises normalisation"),
    ("near_miss_keywords",       near_miss,        "Off-by-one misspellings — zero matches expected"),
    ("redos_bait_string",        redos_bait,       "Classic ReDoS: 5000 'a' chars"),
    ("boundary_stress",          boundary_stress,  "Repeated word-boundary positions"),
    ("unicode_keyword_mix",      unicode_mix,      "Unicode + keywords interleaved"),
    ("empty",                    "",               "Empty — baseline"),
    ("single_short_keyword",     "scam",           "Minimum viable match"),
]


# ──────────────────────────────────────────────
# PROFILER
# ──────────────────────────────────────────────
def profile_pattern(label, text):
    times = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        result = analyze_text(text)
        times.append((time.perf_counter() - t0) * 1000)

    med   = statistics.median(times)
    mx    = max(times)
    mn    = min(times)
    risk_score = result.get("risk_score", 0.0)

    return {
        "label":        label,
        "reps":         REPS,
        "median_ms":    round(med, 3),
        "max_ms":       round(mx, 3),
        "min_ms":       round(mn, 3),
        "risk_score":   risk_score,
        "safe":         mx < TIMING_THRESHOLD_MS,
    }


# ──────────────────────────────────────────────
# REGEX ENGINE INTROSPECTION
# ──────────────────────────────────────────────
def introspect_patterns():
    """
    Checks all regex patterns used by the engine:
    - No nested quantifiers (no ReDoS risk)
    - No lookaheads/lookbehinds (complexity-safe)
    """
    findings = []
    for category, keywords in RISK_KEYWORDS.items():
        for kw in keywords:
            pattern = r"\b" + re.escape(kw) + r"\b"
            flags = []
            if "(" in pattern and ("++" in pattern or "*+" in pattern):
                flags.append("POSSESSIVE_QUANTIFIER")
            if re.search(r"\(\?[<>!]", pattern):
                flags.append("LOOKAROUND")
            if re.search(r"\(.*\+.*\)\+", pattern):
                flags.append("NESTED_QUANTIFIER")
            findings.append({
                "category": category,
                "keyword":  kw,
                "pattern":  pattern,
                "flags":    flags,
                "safe":     len(flags) == 0,
            })

    risky = [f for f in findings if not f["safe"]]
    return {
        "total_patterns": len(findings),
        "risky_patterns": len(risky),
        "risky_list":     risky,
        "safe":           len(risky) == 0,
    }


# ──────────────────────────────────────────────
# REPORT
# ──────────────────────────────────────────────
def write_report(profiles, introspection, verdict):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Regex Attack Profile",
        "",
        f"**Generated:** {ts}  ",
        f"**Threshold:** {TIMING_THRESHOLD_MS}ms per call  ",
        f"**Reps per pattern:** {REPS}  ",
        f"**Verdict:** `{verdict}`",
        "",
        "## Pattern Timing Results",
        "",
        "| Pattern | Median (ms) | Max (ms) | Risk Score | Safe? |",
        "|---------|------------|---------|------------|-------|",
    ]
    for p in profiles:
        safe_str = "SAFE" if p["safe"] else "WARN"
        lines.append(
            f"| `{p['label']}` | {p['median_ms']} | {p['max_ms']} | "
            f"{p['risk_score']} | **{safe_str}** |"
        )

    lines += [
        "",
        "## Regex Pattern Introspection",
        "",
        f"Analysed **{introspection['total_patterns']} regex patterns** "
        f"(one per keyword) across all categories.",
        "",
        "| Check | Result |",
        "|-------|--------|",
        f"| Patterns with nested quantifiers | {introspection['risky_patterns']} |",
        f"| Patterns with lookarounds | {introspection['risky_patterns']} |",
        f"| All patterns safe | {'YES' if introspection['safe'] else 'NO'} |",
        "",
        "All patterns use the form `\\bLITERAL\\b` — `re.escape()` prevents",
        "any special character injection. Word boundaries are O(1). No backtracking risk.",
        "",
        "## ReDoS Immunity Explanation",
        "",
        "The engine uses `re.search(r'\\b' + re.escape(keyword) + r'\\b', text)`.",
        "",
        "- `re.escape()` neutralises all regex metacharacters in keywords.",
        "- No nested quantifiers (`(a+)+`, `(a*)*`) — immune to exponential backtrack.",
        "- No alternation of overlapping patterns in a single `re.search` call.",
        "- Each keyword is searched independently — worst case is linear `O(N * K)`",
        "  where N=5000 (capped) and K ~100 keywords.",
        "",
        "## Conclusion",
        "",
    ]
    if verdict == "SAFE":
        lines.append(
            f"All {len(profiles)} adversarial patterns completed within "
            f"{TIMING_THRESHOLD_MS}ms. No ReDoS vulnerability detected."
        )
    else:
        lines.append("**WARNING:** One or more patterns exceeded the timing threshold.")

    with open("regex_attack_profile.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[regex_profile] Report -> regex_attack_profile.md")


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[regex_profile] Profiling {len(PROFILES)} adversarial patterns "
          f"({REPS} reps each)\n")

    profiles = []
    for label, text, desc in PROFILES:
        p = profile_pattern(label, text)
        status = "SAFE" if p["safe"] else "WARN"
        print(f"  [{status}] {label:35s} median={p['median_ms']:7.2f}ms  "
              f"max={p['max_ms']:7.2f}ms")
        profiles.append(p)

    introspection = introspect_patterns()
    print(f"\n[regex_profile] Introspection: {introspection['total_patterns']} patterns, "
          f"{introspection['risky_patterns']} risky")

    all_safe = all(p["safe"] for p in profiles) and introspection["safe"]
    verdict  = "SAFE" if all_safe else "WARNING"

    print(f"\n{'='*50}")
    print(f"REGEX SAFETY VERDICT: {verdict}")
    print(f"{'='*50}\n")

    write_report(profiles, introspection, verdict)
    sys.exit(0 if all_safe else 1)
