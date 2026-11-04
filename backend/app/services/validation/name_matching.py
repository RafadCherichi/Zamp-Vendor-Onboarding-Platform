import re
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, Optional, Set

LEGAL_SUFFIXES = [
    r"\bprivate\s+limited\b",
    r"\bpvt\.?\s*ltd\.?\b",
    r"\blimited\b",
    r"\bltd\.?\b",
    r"\blimited\s+liability\s+partnership\b",
    r"\bllp\b",
    r"\benterprises\b",
    r"\bcompany\b",
    r"\bcorp\.?\b",
    r"\bcorporation\b",
    r"\bco\.?\b",
    r"\bm/s\.?\b",
    r"\bprop\.?\b",
    r"\bproprietor\b",
    r"\band\b",
    r"\&",
]


class NameMatchOutcome(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    NORMALISED_MATCH = "NORMALISED_MATCH"
    PROBABLE_MATCH = "PROBABLE_MATCH"
    SIGNIFICANT_MISMATCH = "SIGNIFICANT_MISMATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


MatchTier = NameMatchOutcome


@dataclass
class NameMatchResult:
    outcome: NameMatchOutcome
    similarity_score: float
    submitted_name: str
    target_name: str
    explanation: str
    is_acceptable_match: bool  # True for exact and normalised; False/Review for probable or mismatch

    def __iter__(self):
        yield self.outcome
        yield self.similarity_score
        yield self.explanation


def normalise_name_string(raw_name: str, strip_legal_suffixes: bool = True) -> str:
    """
    Normalises legal/trade name for comparison by removing case differences,
    special characters, repeated whitespace, and optionally common legal entity suffixes.
    """
    if not raw_name:
        return ""

    text = raw_name.lower().strip()

    if strip_legal_suffixes:
        for suffix_pat in LEGAL_SUFFIXES:
            text = re.sub(suffix_pat, " ", text, flags=re.IGNORECASE)

    # Strip punctuation and non-alphanumeric (keep only letters and digits)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_levenshtein_ratio(s1: str, s2: str) -> float:
    """Computes normalized Levenshtein similarity ratio between 0.0 and 1.0."""
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    len1, len2 = len(s1), len(s2)
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # deletion
                dp[i][j - 1] + 1,      # insertion
                dp[i - 1][j - 1] + cost # substitution
            )

    dist = dp[len1][len2]
    max_len = max(len1, len2)
    return round(1.0 - (dist / max_len), 3)


def compute_token_jaccard(s1: str, s2: str) -> float:
    """Computes token set Jaccard similarity."""
    t1 = set(s1.split())
    t2 = set(s2.split())
    if not t1 or not t2:
        return 0.0
    intersection = t1 & t2
    union = t1 | t2
    return round(len(intersection) / len(union), 3)


def compare_names(submitted: Optional[str], target: Optional[str], entity_type: Optional[str] = None) -> NameMatchResult:
    """
    Entity-aware name comparison supporting 5 tiers:
    - EXACT_MATCH: identical characters
    - NORMALISED_MATCH: identical after suffix & punctuation removal
    - PROBABLE_MATCH: 0.80 to 0.99 similarity (flagged as WARNING for review)
    - SIGNIFICANT_MISMATCH: < 0.80 similarity (FAILED)
    - INSUFFICIENT_EVIDENCE: empty input
    """
    sub_clean = (submitted or "").strip()
    tar_clean = (target or "").strip()

    if not sub_clean or not tar_clean:
        return NameMatchResult(
            outcome=NameMatchOutcome.INSUFFICIENT_EVIDENCE,
            similarity_score=0.0,
            submitted_name=sub_clean,
            target_name=tar_clean,
            explanation="Insufficient evidence: Name was missing from application or document extraction.",
            is_acceptable_match=False,
        )

    # 1. Exact Match (case-insensitive after trim)
    if sub_clean.upper() == tar_clean.upper():
        return NameMatchResult(
            outcome=NameMatchOutcome.EXACT_MATCH,
            similarity_score=1.0,
            submitted_name=sub_clean,
            target_name=tar_clean,
            explanation="Exact match: Names are character-for-character identical.",
            is_acceptable_match=True,
        )

    # 2. Normalised Match (strip punctuation and legal suffixes)
    norm_sub = normalise_name_string(sub_clean, strip_legal_suffixes=True)
    norm_tar = normalise_name_string(tar_clean, strip_legal_suffixes=True)

    if norm_sub == norm_tar and len(norm_sub) > 2:
        return NameMatchResult(
            outcome=NameMatchOutcome.NORMALISED_MATCH,
            similarity_score=1.0,
            submitted_name=sub_clean,
            target_name=tar_clean,
            explanation="Normalised match: Names match once legal suffixes (e.g. Pvt Ltd, LLP) and punctuation are standard-formatted.",
            is_acceptable_match=True,
        )

    # 3. Probable Match vs Significant Mismatch
    lev_score = compute_levenshtein_ratio(norm_sub, norm_tar)
    token_score = compute_token_jaccard(norm_sub, norm_tar)
    combined_score = max(lev_score, token_score)

    # Check for token subset (e.g. "Apex Components" vs "Apex Components & Fasteners")
    sub_tokens = set(norm_sub.split())
    tar_tokens = set(norm_tar.split())
    is_subset = sub_tokens.issubset(tar_tokens) or tar_tokens.issubset(sub_tokens)

    if combined_score >= 0.80 or (is_subset and len(sub_tokens & tar_tokens) >= 2):
        score = max(combined_score, 0.85 if is_subset else 0.80)
        return NameMatchResult(
            outcome=NameMatchOutcome.PROBABLE_MATCH,
            similarity_score=round(score, 2),
            submitted_name=sub_clean,
            target_name=tar_clean,
            explanation=f"Probable match ({int(score * 100)}% similarity): Word variation or abbreviation detected between submitted name and document evidence. Human verification recommended.",
            is_acceptable_match=False,  # Escalated as Warning
        )

    return NameMatchResult(
        outcome=NameMatchOutcome.SIGNIFICANT_MISMATCH,
        similarity_score=round(combined_score, 2),
        submitted_name=sub_clean,
        target_name=tar_clean,
        explanation=f"Significant mismatch ({int(combined_score * 100)}% similarity): Submitted entity name does not align with document evidence.",
        is_acceptable_match=False,
    )
