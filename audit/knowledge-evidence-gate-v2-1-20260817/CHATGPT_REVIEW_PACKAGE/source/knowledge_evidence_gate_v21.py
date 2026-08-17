"""Generic, offline Gate V2.1 evidence semantics.

This module deliberately contains no sample identifiers, filesystem roots, model
loading, audio decoding, network calls, or production writes.  It consumes the
already frozen evidence rows and separates source binding, temporal alignment,
lexical diagnostics, semantic supporting signals, critical signatures, and
knowledge acceptance.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Iterable, Mapping, Sequence


CRITICAL_RISK_TYPES = {"NUMBER", "FORMULA", "TERM", "SYMBOL", "INDEXED_SYMBOL"}
NONCRITICAL_RISK_TYPES = {"CLEAN_CONTROL", "MODULE_COVERAGE_UNKNOWN", ""}
PROMOTIONAL_MARKERS = (
    "请不吝点赞",
    "订阅",
    "转发",
    "打赏支持",
    "明镜与点点栏目",
    "promotional",
    "promo speech",
)
UNIT_FAMILIES = {
    "公里": "distance_km",
    "千米": "distance_km",
    "km": "distance_km",
    "kilometer": "distance_km",
    "kilometers": "distance_km",
    "mile": "distance_mile",
    "miles": "distance_mile",
    "mph": "speed_mph",
    "mile per hour": "speed_mph",
    "miles per hour": "speed_mph",
    "英里每小时": "speed_mph",
    "英里/小时": "speed_mph",
    "米": "distance_m",
    "meter": "distance_m",
    "meters": "distance_m",
    "%": "percent",
    "百分比": "percent",
}
EN_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
ZH_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _as_text(value: Any) -> str:
    return "" if value is None else str(value)


def normalize_text(text: Any) -> str:
    """Normalize punctuation and case for diagnostics, never for source data."""

    value = _as_text(text).lower()
    value = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", value)
    value = re.sub(r"[^\w\u4e00-\u9fff.%+\-/=<>*^() ]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def detect_language(text: Any) -> str:
    value = _as_text(text)
    zh = len(re.findall(r"[\u4e00-\u9fff]", value))
    latin = len(re.findall(r"[A-Za-z]", value))
    if zh and latin:
        return "mixed"
    if zh:
        return "zh"
    if latin:
        return "en"
    return "unknown"


def is_cross_lingual(source_text: Any, audio_text: Any) -> bool:
    source_lang = detect_language(source_text)
    audio_lang = detect_language(audio_text)
    return {source_lang, audio_lang} >= {"zh", "en"} or (
        source_lang == "mixed" and audio_lang == "en"
    )


def lexical_alignment_score(source_text: Any, audio_text: Any) -> float:
    """Token-overlap diagnostic; it is never an acceptance gate."""

    source = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", normalize_text(source_text)))
    audio = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", normalize_text(audio_text)))
    if not source or not audio:
        return 0.0
    return len(source & audio) / max(1, len(source))


def _chinese_number(text: str) -> str | None:
    """Convert the common spoken Chinese number forms used in the fixtures."""

    chars = [c for c in text if c in ZH_DIGITS or c in "十百千万点"]
    if not chars:
        return None
    if "点" in chars:
        left, right = "".join(chars).split("点", 1)
        left_value = _chinese_number(left) or "0"
        right_digits = "".join(str(ZH_DIGITS[c]) for c in right if c in ZH_DIGITS)
        return f"{left_value}.{right_digits}" if right_digits else left_value
    if all(c in ZH_DIGITS for c in chars):
        return "".join(str(ZH_DIGITS[c]) for c in chars)
    total = 0
    current = 0
    multipliers = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    for c in chars:
        if c in ZH_DIGITS:
            current = ZH_DIGITS[c]
        elif c in multipliers:
            unit = multipliers[c]
            total += (current or 1) * unit
            current = 0
    value = total + current
    return str(value) if value else None


def _english_number_words(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", normalize_text(text))
    result: list[str] = []
    current = 0
    active = False
    for word in words:
        if word not in EN_NUMBER_WORDS:
            if active:
                result.append(str(current))
                current = 0
                active = False
            continue
        value = EN_NUMBER_WORDS[word]
        active = True
        if value in (20, 30, 40, 50, 60, 70, 80, 90) and current:
            current += value
        else:
            current = current + value if current else value
    if active:
        result.append(str(current))
    return result


def _number_tokens(text: Any) -> list[str]:
    value = _as_text(text)
    tokens: list[str] = []
    # Parse Chinese fractions as a unit, then remove them from the generic scan
    # so nearby words such as "一切" do not create a spurious number token.
    consumed: list[tuple[int, int]] = []
    fraction_pattern = r"([零〇一二两三四五六七八九十百千万点]+|\d+)\s*分之\s*([零〇一二两三四五六七八九十百千万点]+|\d+)"
    for match in re.finditer(fraction_pattern, value):
        numerator = _chinese_number(match.group(1)) if not match.group(1).isdigit() else match.group(1)
        denominator = _chinese_number(match.group(2)) if not match.group(2).isdigit() else match.group(2)
        if numerator is not None:
            tokens.append(numerator)
        if denominator is not None:
            tokens.append(denominator)
        consumed.append(match.span())
    residual = list(value)
    for start, end in consumed:
        for i in range(start, end):
            residual[i] = " "
    residual_text = "".join(residual)
    tokens.extend(re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?", residual_text))
    tokens.extend(_english_number_words(residual_text))
    # Ordinary Chinese characters are not treated as numbers unless they form
    # an actual multi-character number sequence or decimal expression.
    for match in re.finditer(r"[零〇一二两三四五六七八九十百千万点]+", residual_text):
        if len(match.group(0)) == 1 and match.group(0) in ZH_DIGITS:
            continue
        converted = _chinese_number(match.group(0))
        if converted is not None:
            tokens.append(converted)
    return tokens


def _unit_tokens(text: Any) -> list[str]:
    value = normalize_text(text)
    found: list[str] = []
    for unit in sorted(UNIT_FAMILIES, key=len, reverse=True):
        if unit in value:
            found.append(UNIT_FAMILIES[unit])
    return found


def has_fraction(text: Any) -> bool:
    value = normalize_text(text)
    return bool(re.search(r"\b\d+\s*/\s*\d+\b", value) or re.search(r"[一二两三四五六七八九十百]+分之[一二两三四五六七八九十百]+", _as_text(text)) or re.search(r"\b(?:one|a)\s+(?:half|third|quarter)\b", value))


def has_ambiguous_numeric_tokenization(text: Any) -> bool:
    value = _as_text(text)
    return bool(re.search(r"(?:除|加|减|乘|divide|plus|minus|times)\s*\d{3,}", value, re.I))


def indexed_symbol_signature(text: Any) -> set[str]:
    value = normalize_text(text)
    symbols = {f"{letter.upper()}{index}" for letter, index in re.findall(r"(?<![A-Za-z0-9])([A-Za-z])(\d+)(?![A-Za-z0-9])", value)}
    symbols.update(f"{index}{letter.upper()}" for index, letter in re.findall(r"(?<![A-Za-z0-9])(\d+)([A-Za-z])(?![A-Za-z0-9])", value))
    # Spoken/ASR spacing often separates the letter and index ("a 1 b 2").
    symbols.update(f"{letter.upper()}{index}" for letter, index in re.findall(r"(?<![A-Za-z])([A-Za-z])\s+(\d+)(?!\d)", value))
    return symbols


def symbol_letter_signature(text: Any) -> set[str]:
    value = _as_text(text)
    # Case-sensitive uppercase matching avoids treating ordinary English
    # articles ("a") as mathematical symbols.
    return {x for x in re.findall(r"(?<![A-Za-z])[A-Z](?![A-Za-z])", value) if x != "I"}


def number_signature(text: Any) -> tuple[str, ...]:
    result = _number_tokens(text)
    # Preserve ordered occurrences: order matters for sequences and formulas.
    return tuple(result)


def number_with_unit_signature(text: Any) -> tuple[tuple[str, str], ...]:
    numbers = number_signature(text)
    units = _unit_tokens(text)
    if not numbers or not units:
        return ()
    return tuple((n, units[i] if i < len(units) else units[-1]) for i, n in enumerate(numbers))


def formula_signature(text: Any) -> tuple[str, ...]:
    value = normalize_text(text)
    tokens = re.findall(r"[a-z]+|\d+(?:\.\d+)?|[=<>*/^+\-()]", value)
    return tuple(tokens)


def term_signature(text: Any) -> tuple[str, ...]:
    stop = {"the", "a", "an", "and", "of", "from", "to", "is", "are", "叫做", "一本书"}
    return tuple(x for x in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", normalize_text(text)) if x not in stop)


def infer_knowledge_type(text: Any, declared_type: Any = "") -> str:
    value = _as_text(text)
    declared = _as_text(declared_type).upper()
    if indexed_symbol_signature(value):
        return "INDEXED_SYMBOL"
    if has_fraction(value):
        return "FRACTION"
    if _unit_tokens(value) and number_signature(value):
        return "NUMBER_WITH_UNIT"
    if re.search(r"[=<>]|(?:sin|cos|log|integral|公式|方程|函数)", value, re.I):
        return "FORMULA"
    if declared in {"TERM", "TERM_OR_STATEMENT"}:
        words = term_signature(value)
        if len(words) >= 3 and ("book" in words or "series" in words or "proof" in words):
            return "NAMED_TITLE_OR_TERM"
        return "TERM"
    if symbol_letter_signature(value) and number_signature(value):
        return "SYMBOL_LETTER"
    if number_signature(value):
        return "NUMBER"
    if declared in {"FORMULA", "NUMBER", "SYMBOL", "INDEXED_SYMBOL"}:
        return declared
    return "TERM_OR_STATEMENT"


def source_binding_state(evidence: Mapping[str, Any]) -> str:
    required = ("episode_key", "cue_index", "cue_start", "cue_end", "audio_sha256", "clip_sha256")
    present = all(_as_text(evidence.get(k)).strip() for k in required)
    declared = evidence.get("source_binding")
    declared_ok = declared is True or _as_text(declared).lower() == "true"
    return "SOURCE_BOUND" if present and declared_ok else "SOURCE_BINDING_FAILED"


def temporal_alignment_state(evidence: Mapping[str, Any]) -> str:
    text = _as_text(evidence.get("audio_window_text") or evidence.get("transcribed_text"))
    if any(marker.lower() in text.lower() for marker in PROMOTIONAL_MARKERS):
        return "TEMPORAL_FAILED"
    try:
        start = float(evidence.get("window_start_seconds"))
        end = float(evidence.get("window_end_seconds"))
        duration = float(evidence.get("audio_duration_seconds"))
    except (TypeError, ValueError):
        return "TEMPORAL_UNKNOWN"
    if start < 0 or end <= start or end > duration + 0.25:
        return "TEMPORAL_FAILED"
    return "TEMPORAL_VERIFIED"


def _same_or_subset(left: Sequence[Any], right: Sequence[Any]) -> str:
    if not left or not right:
        return "SIGNATURE_UNKNOWN"
    if list(left) == list(right):
        return "SIGNATURE_MATCH"
    if list(left) == list(right)[: len(left)] or set(left).issubset(set(right)):
        return "SIGNATURE_PARTIAL"
    return "SIGNATURE_MISMATCH"


def critical_signature_state(source_text: Any, audio_text: Any, knowledge_type: str, *, expanded_window: bool = False) -> str:
    kind = knowledge_type.upper()
    if kind == "NUMBER_WITH_UNIT":
        source = number_with_unit_signature(source_text)
        audio = number_with_unit_signature(audio_text)
        if source and audio and source == audio:
            return "SIGNATURE_MATCH"
        if source and audio and [n for n, _ in source] == [n for n, _ in audio]:
            return "SIGNATURE_MISMATCH"
        return "SIGNATURE_UNKNOWN"
    if kind == "FRACTION":
        source = number_signature(source_text)
        audio = number_signature(audio_text)
        if source and audio and source == audio:
            return "SIGNATURE_MATCH"
        return _same_or_subset(source, audio)
    if kind == "INDEXED_SYMBOL":
        return _same_or_subset(sorted(indexed_symbol_signature(source_text)), sorted(indexed_symbol_signature(audio_text)))
    if kind == "SYMBOL_LETTER":
        return _same_or_subset(sorted(symbol_letter_signature(source_text)), sorted(symbol_letter_signature(audio_text)))
    if kind == "FORMULA":
        return _same_or_subset(formula_signature(source_text), formula_signature(audio_text))
    if kind in {"TERM", "NAMED_TITLE_OR_TERM"}:
        source = set(term_signature(source_text))
        audio = set(term_signature(audio_text))
        if source and source.issubset(audio):
            return "SIGNATURE_MATCH"
        return "SIGNATURE_MISMATCH" if source and audio else "SIGNATURE_UNKNOWN"
    source = number_signature(source_text)
    audio = number_signature(audio_text)
    if has_ambiguous_numeric_tokenization(audio_text):
        return "SIGNATURE_UNKNOWN"
    if expanded_window and source and audio and set(source).issubset(set(audio)) and len(audio) > len(source):
        return "SIGNATURE_PARTIAL"
    return _same_or_subset(source, audio)


def extractor_state(declared_type: Any, inferred_type: str) -> str:
    declared = _as_text(declared_type).upper()
    if not declared:
        return "EXTRACTOR_UNKNOWN"
    # A structured reclassification is a taxonomy decision, not an extractor
    # error.  In particular, indexed symbols are not ordinary NUMBER units.
    if declared == "NUMBER" and inferred_type in {"INDEXED_SYMBOL", "SYMBOL_LETTER", "NUMBER_WITH_UNIT", "FRACTION"}:
        return "EXTRACTOR_CONSISTENT"
    if declared in {"TERM", "TERM_OR_STATEMENT"} and inferred_type in {"TERM", "NAMED_TITLE_OR_TERM"}:
        return "EXTRACTOR_CONSISTENT"
    if declared == inferred_type or (declared == "FORMULA" and inferred_type == "FORMULA"):
        return "EXTRACTOR_CONSISTENT"
    return "EXTRACTOR_TYPE_MISMATCH"


def semantic_alignment_state(source_text: Any, audio_text: Any, temporal_state: str) -> str:
    if temporal_state == "TEMPORAL_FAILED":
        return "SEMANTIC_UNRELATED_OR_WRONG_WINDOW"
    if is_cross_lingual(source_text, audio_text):
        return "SEMANTIC_SUPPORTING_SIGNAL_CROSS_LANGUAGE"
    score = lexical_alignment_score(source_text, audio_text)
    return "SEMANTIC_SUPPORTING_SIGNAL" if score >= 0.2 else "SEMANTIC_UNKNOWN"


def is_critical(evidence: Mapping[str, Any]) -> bool:
    kind = _as_text(evidence.get("sample_kind")).upper()
    risk = _as_text(evidence.get("risk_type")).upper()
    return kind == "UNCERTAINTY" and risk not in NONCRITICAL_RISK_TYPES


def assess_evidence(pair: Mapping[str, Any], audio: Mapping[str, Any]) -> dict[str, Any]:
    """Assess one fixed evidence unit without knowing its sample identifier."""

    source_text = pair.get("original_text", "")
    audio_text = audio.get("audio_window_text") or audio.get("transcribed_text") or pair.get("b_text", "")
    declared_type = pair.get("knowledge_type") or pair.get("risk_type")
    inferred_type = infer_knowledge_type(source_text, declared_type)
    critical = is_critical(pair)
    bound = source_binding_state({**pair, **audio})
    temporal = temporal_alignment_state({**pair, **audio})
    cross_language = is_cross_lingual(source_text, audio_text)
    legacy_score = pair.get("alignment_score")
    try:
        lexical = float(legacy_score)
    except (TypeError, ValueError):
        lexical = lexical_alignment_score(source_text, audio_text)
    expanded = len(number_signature(audio_text)) > len(number_signature(source_text)) and bool(number_signature(source_text))
    signature = critical_signature_state(source_text, audio_text, inferred_type, expanded_window=expanded)
    extract_state = extractor_state(declared_type, inferred_type)
    audio_state = _as_text(audio.get("audio_state") or pair.get("audio_state") or "AUDIO_UNKNOWN").upper()
    if audio_state not in {"AUDIO_RECOVERABLE", "AUDIO_UNRECOVERABLE", "AUDIO_UNKNOWN"}:
        audio_state = "AUDIO_UNKNOWN"
    semantic = semantic_alignment_state(source_text, audio_text, temporal)
    reason = ""
    human_review = False
    text_only_correction = False
    if bound != "SOURCE_BOUND":
        acceptance = "BLOCKED_CRITICAL" if critical else "PRESERVED_ORIGINAL"
        reason = "source binding evidence is incomplete"
    elif not critical:
        if _as_text(pair.get("sample_kind")).upper() == "CLEAN_CONTROL" and temporal == "TEMPORAL_FAILED":
            acceptance = "PRESERVED_ORIGINAL"
            reason = "clean control retains original when temporal evidence fails"
        elif temporal == "TEMPORAL_VERIFIED" and audio_state == "AUDIO_RECOVERABLE":
            acceptance = "ACCEPTED_AUDIO_BOUND"
            reason = "noncritical audio-bound evidence accepted; original remains preserved"
        else:
            acceptance = "PRESERVED_ORIGINAL"
            reason = "noncritical evidence not admitted as a correction"
    elif audio_state != "AUDIO_RECOVERABLE":
        acceptance = "BLOCKED_CRITICAL"
        reason = "critical audio is not recoverable"
    elif temporal != "TEMPORAL_VERIFIED":
        acceptance = "BLOCKED_CRITICAL"
        reason = "critical temporal alignment is not verified"
        human_review = True
    elif extract_state == "EXTRACTOR_TYPE_MISMATCH":
        acceptance = "BLOCKED_CRITICAL"
        reason = "generic extractor taxonomy mismatch"
        human_review = True
    elif signature == "SIGNATURE_MATCH":
        acceptance = "ACCEPTED_AUDIO_BOUND"
        reason = "critical signature matches within source-bound temporal evidence"
    else:
        acceptance = "BLOCKED_CRITICAL"
        reason = f"critical signature state is {signature}"
        human_review = True
    return {
        "sample_id": pair.get("sample_id", ""),
        "sample_kind": pair.get("sample_kind", ""),
        "episode_key": pair.get("episode_key", ""),
        "risk_type": pair.get("risk_type", ""),
        "declared_knowledge_type": declared_type or "",
        "inferred_knowledge_type": inferred_type,
        "source_language": detect_language(source_text),
        "audio_text_language": detect_language(audio_text),
        "cross_lingual": cross_language,
        "source_binding": bound,
        "audio_state": audio_state,
        "temporal_state": temporal,
        "lexical_alignment_score": lexical,
        "semantic_alignment_state": semantic,
        "critical_signature_state": signature if critical else "SIGNATURE_NOT_APPLICABLE",
        "extractor_state": extract_state,
        "knowledge_acceptance": acceptance,
        "original_text": source_text,
        "audio_text": audio_text,
        "cue_start": pair.get("cue_start", ""),
        "cue_end": pair.get("cue_end", ""),
        "clip_start": audio.get("window_start_seconds", ""),
        "clip_end": audio.get("window_end_seconds", ""),
        "audio_sha256": audio.get("audio_sha256") or pair.get("audio_sha256", ""),
        "clip_sha256": audio.get("clip_sha256") or pair.get("clip_sha256", ""),
        "source_binding_ok": bound == "SOURCE_BOUND",
        "text_only_correction": text_only_correction,
        "full_cue_transcript_rewrite": False,
        "clean_control_harmful_change": False,
        "human_review_required": human_review,
        "reason": reason,
        "legacy_alignment_score_diagnostic_only": True,
        "translation_or_llm_used": False,
    }


def compute_gate(assessments: Iterable[Mapping[str, Any]], *, sample_total: int | None = None) -> dict[str, Any]:
    rows = list(assessments)
    unique_ids = {r.get("sample_id") for r in rows if r.get("sample_id")}
    critical = [r for r in rows if is_critical(r)]
    controls = [r for r in rows if _as_text(r.get("sample_kind")).upper() == "CLEAN_CONTROL"]
    blocked = [r for r in critical if r.get("knowledge_acceptance") == "BLOCKED_CRITICAL"]
    accepted = [r for r in critical if r.get("knowledge_acceptance") == "ACCEPTED_AUDIO_BOUND"]
    extractor_errors = [r for r in critical if r.get("extractor_state") == "EXTRACTOR_TYPE_MISMATCH"]
    source_failures = [r for r in rows if r.get("source_binding") != "SOURCE_BOUND"]
    text_only = [r for r in rows if r.get("text_only_correction")]
    harmful_controls = [r for r in controls if r.get("clean_control_harmful_change")]
    wrong_accepts = [r for r in critical if r.get("knowledge_acceptance") == "ACCEPTED_AUDIO_BOUND" and r.get("critical_signature_state") in {"SIGNATURE_MISMATCH", "SIGNATURE_UNKNOWN", "SIGNATURE_PARTIAL"}]
    false_negatives = [r for r in critical if r.get("wrongly_accepted_critical")]
    hard = {
        "critical_false_negative_count": len(false_negatives),
        "wrongly_accepted_critical_count": len(wrong_accepts),
        "extractor_critical_error_count": len(extractor_errors),
        "critical_source_binding_failure": sum(1 for r in source_failures if is_critical(r)),
        "text_only_correction_accepted_count": len(text_only),
        "clean_control_harmful_change_count": len(harmful_controls),
    }
    hard_fail = any(v > 0 for v in hard.values())
    if hard_fail:
        decision = "FAIL"
    elif blocked:
        decision = "CONDITIONAL_PASS"
    else:
        decision = "PASS"
    return {
        "stage": "V2.1",
        "sample_total": sample_total if sample_total is not None else len(rows),
        "unique_sample_ids": len(unique_ids),
        "uncertainty_sample_count": sum(1 for r in rows if _as_text(r.get("sample_kind")).upper() == "UNCERTAINTY"),
        "clean_control_count": len(controls),
        "critical_units_total": len(critical),
        "accepted_critical_count": len(accepted),
        "blocked_critical_count": len(blocked),
        "wrongly_accepted_critical_count": len(wrong_accepts),
        "critical_false_negative_count": len(false_negatives),
        "extractor_critical_error_count": len(extractor_errors),
        "critical_source_binding_failure": hard["critical_source_binding_failure"],
        "text_only_correction_accepted_count": len(text_only),
        "clean_control_harmful_change_count": len(harmful_controls),
        "hard_fail_conditions": hard,
        "gate_decision": decision,
        "limited_canary_eligible": False,
        "full_scale_authorized": False,
        "knowledge_canary_authorized": False,
        "coverage_and_safety_separated": True,
        "decision_basis": "Critical evidence is admitted only when source binding, temporal evidence, type-specific signature, and generic extractor consistency are all satisfied; unresolved critical units remain quarantined.",
    }


def text_only_correction_is_forbidden(result: Mapping[str, Any]) -> bool:
    return bool(result.get("text_only_correction")) or bool(result.get("full_cue_transcript_rewrite"))


def source_binding_required(result: Mapping[str, Any]) -> bool:
    return result.get("knowledge_acceptance") == "ACCEPTED_AUDIO_BOUND" and result.get("source_binding") == "SOURCE_BOUND"


__all__ = [
    "assess_evidence",
    "compute_gate",
    "critical_signature_state",
    "detect_language",
    "extractor_state",
    "formula_signature",
    "has_ambiguous_numeric_tokenization",
    "infer_knowledge_type",
    "indexed_symbol_signature",
    "is_critical",
    "lexical_alignment_score",
    "number_signature",
    "number_with_unit_signature",
    "source_binding_required",
    "source_binding_state",
    "temporal_alignment_state",
    "term_signature",
    "text_only_correction_is_forbidden",
]
