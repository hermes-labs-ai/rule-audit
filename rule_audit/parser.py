"""
rule_audit/parser.py

Parses a system prompt into structured Rule objects using NLP heuristics:
- Sentence boundary splitting
- Modal verb detection (must, should, may, can, will, shall)
- Negation detection (never, not, no, don't, cannot, refuse)
- Absoluteness scoring (always/never = 1.0, should/may = 0.5)
- Rule type classification (permission, prohibition, obligation, preference, meta)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Modality(str, Enum):
    MUST = "must"  # strong obligation
    MUST_NOT = "must_not"  # strong prohibition
    SHOULD = "should"  # soft obligation
    SHOULD_NOT = "should_not"
    MAY = "may"  # permission
    MAY_NOT = "may_not"
    UNKNOWN = "unknown"


class RuleType(str, Enum):
    OBLIGATION = "obligation"  # you must do X
    PROHIBITION = "prohibition"  # never do X
    PERMISSION = "permission"  # you may do X
    PREFERENCE = "preference"  # prefer X over Y
    META = "meta"  # rules about how to apply rules
    IDENTITY = "identity"  # you are / you are not
    GOAL = "goal"  # your goal / purpose is
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class Rule:
    text: str
    sentence_index: int
    modality: Modality = Modality.UNKNOWN
    rule_type: RuleType = RuleType.UNKNOWN
    absoluteness: float = 0.0  # 0.0 (soft) → 1.0 (absolute)
    negated: bool = False
    subject: str = ""  # what entity the rule applies to
    action: str = ""  # what action/behavior is regulated
    condition: str = ""  # if/when clause, if present
    keywords: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"Rule(idx={self.sentence_index}, modality={self.modality.value}, "
            f"type={self.rule_type.value}, abs={self.absoluteness:.2f}, "
            f"negated={self.negated}, text={self.text[:60]!r})"
        )


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Modal verb patterns — order matters (more specific first)
_MODAL_PATTERNS: list[tuple[str, Modality]] = [
    # Hard prohibitions
    (r"\b(must\s+not|mustn'?t|shall\s+not|shan'?t)\b", Modality.MUST_NOT),
    (r"\b(cannot|can'?t|will\s+not|won'?t|do\s+not|don'?t|never)\b", Modality.MUST_NOT),
    (
        r"\b(refuse|deny|reject|decline|forbid|prohibited?|not\s+allowed)\b",
        Modality.MUST_NOT,
    ),
    # Hard obligations
    (r"\b(must|shall|have\s+to|need\s+to|required?\s+to|always)\b", Modality.MUST),
    (r"\b(will\s+always|always\s+will|ensure\s+that|make\s+sure)\b", Modality.MUST),
    # Soft prohibitions
    (r"\b(should\s+not|shouldn'?t|avoid|refrain\s+from)\b", Modality.SHOULD_NOT),
    # Soft obligations
    (
        r"\b(should|ought\s+to|try\s+to|attempt\s+to|strive\s+to|aim\s+to)\b",
        Modality.SHOULD,
    ),
    # Permissions
    (r"\b(may\s+not|cannot\s+be\s+allowed)\b", Modality.MAY_NOT),
    (
        r"\b(may|can|are\s+allowed\s+to|feel\s+free\s+to|permitted?\s+to)\b",
        Modality.MAY,
    ),
    # Imperative directives (bare verb at start of sentence or after punctuation)
    # These are often injected override attempts: "Ignore ...", "Disregard ..."
    (r"^(ignore|disregard|forget|bypass|override|dismiss)\b", Modality.MUST),
]

# Absoluteness keywords
_ABSOLUTE_KEYWORDS = {
    "never": 1.0,
    "always": 1.0,
    "absolutely": 1.0,
    "under no circumstances": 1.0,
    "at all times": 1.0,
    "in all cases": 1.0,
    "without exception": 1.0,
    "regardless": 0.9,
    "no matter what": 1.0,
    "unconditionally": 1.0,
    "every": 0.8,
    "any": 0.7,
    "all": 0.8,
    "should": 0.5,
    "generally": 0.4,
    "typically": 0.4,
    "usually": 0.4,
    "may": 0.3,
    "can": 0.3,
    "sometimes": 0.2,
    "often": 0.3,
}

# Rule type classifiers
_RULE_TYPE_PATTERNS: list[tuple[str, RuleType]] = [
    (
        r"\b(you are|you're|act as|behave as|your (role|identity|name) is)\b",
        RuleType.IDENTITY,
    ),
    (r"\b(your (goal|purpose|mission|task|job|objective|aim) is)\b", RuleType.GOAL),
    # Meta rules — rules about how to handle rules
    (
        r"\b(priorit|override|supersede|take precedence|trump|when.*conflict|if.*rules?.*conflict)\b",
        RuleType.META,
    ),
    (
        r"\b(these (instructions?|rules?|guidelines?)|above (instructions?|rules?))\b",
        RuleType.META,
    ),
    (
        r"\b(interpret|apply|follow|adhere to).*(rule|guideline|instruction|policy)\b",
        RuleType.META,
    ),
    # Prohibitions
    (
        r"\b(never|must not|cannot|refuse|forbidden|prohibited|do not|don'?t)\b",
        RuleType.PROHIBITION,
    ),
    # Permissions
    (r"\b(may|can|allowed|permitted|feel free)\b", RuleType.PERMISSION),
    # Preferences
    (r"\b(prefer|prioritize|favor|rather|instead of|over)\b", RuleType.PREFERENCE),
    # Obligations
    (r"\b(must|always|shall|required|have to|need to|ensure)\b", RuleType.OBLIGATION),
]

# Negation words
_NEGATION_RE = re.compile(
    r"\b(not|never|no\b|neither|nor|without|don'?t|doesn'?t|didn'?t|"
    r"won'?t|wouldn'?t|can'?t|cannot|mustn'?t|shouldn'?t|haven'?t|"
    r"hasn'?t|hadn'?t|refuse|deny|avoid|prevent|prohibit|forbid)\b",
    re.IGNORECASE,
)

# Condition clauses
_CONDITION_RE = re.compile(
    r"\b(if|when|unless|except|in case|provided that|assuming|given that|"
    r"as long as|only if|whenever|in the event)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Sentence splitter
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    """
    Split on sentence boundaries while preserving bullet points and numbered
    lists as individual sentences.
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split on newline-based list items first
    lines = text.split("\n")
    sentences: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove common list markers
        line = re.sub(r"^[-*•·▪►>]+\s*", "", line)
        line = re.sub(r"^\d+[.)]\s*", "", line)

        if not line:
            continue

        # Further split on sentence terminators within the line
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", line)
        sentences.extend(p.strip() for p in parts if p.strip())

    return sentences


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------


def _detect_modality(text: str) -> Modality:
    lower = text.lower()
    for pattern, modality in _MODAL_PATTERNS:
        if re.search(pattern, lower):
            return modality
    return Modality.UNKNOWN


def _detect_rule_type(text: str) -> RuleType:
    lower = text.lower()
    for pattern, rtype in _RULE_TYPE_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return rtype
    return RuleType.UNKNOWN


def _compute_absoluteness(text: str) -> float:
    lower = text.lower()
    score = 0.0
    found = False
    for kw, val in _ABSOLUTE_KEYWORDS.items():
        if kw in lower:
            score = max(score, val)
            found = True
    if not found:
        # Default: if modal is detected treat as moderate
        score = 0.5
    return score


def _has_negation(text: str) -> bool:
    return bool(_NEGATION_RE.search(text))


def _extract_condition(text: str) -> str:
    m = _CONDITION_RE.search(text)
    if not m:
        return ""
    # Return the clause from the condition word onwards
    return text[m.start() :].strip()


def _extract_keywords(text: str) -> list[str]:
    """Extract significant topical keywords for matching.

    Excludes common stop words AND modal/deontic tokens. Without the modal
    filter, two sentences like "you must always X" and "you must never Y"
    share the keyword "must" and get flagged as a contradiction on trivial
    non-overlapping topics. Keywords should be topical, not modal.
    """
    stop = {
        # Articles / copulas / connectives
        "a", "an", "the", "is", "are", "be", "to", "of", "in", "on", "at",
        "for", "with", "and", "or", "but", "that", "this", "it", "its",
        "you", "your", "i", "my", "we", "our", "they", "their", "as", "by",
        "from", "about", "into", "through", "during", "also", "very",
        # Modal / deontic tokens — these belong to rule modality, not topic.
        # Keeping them out of keywords prevents cross-topic false positives
        # from any two rules that share a modal verb.
        "must", "should", "may", "might", "can", "could", "would", "shall",
        "will", "ought", "need", "have", "has", "had",
        "never", "always", "sometimes", "often", "rarely", "usually",
        "not", "no", "none", "any",
        "do", "does", "did", "done",
    }
    tokens = re.findall(r"[a-z]+", text.lower())
    return [t for t in tokens if t not in stop and len(t) > 2]


def parse(prompt: str) -> list[Rule]:
    """
    Parse a system prompt string into a list of Rule objects.

    Each sentence that contains a normative signal (modal verb, negation,
    directive language) is extracted as a Rule.
    """
    logger.debug("parse: splitting prompt (%d chars)", len(prompt))
    sentences = _split_sentences(prompt)
    logger.debug("parse: %d candidate sentences", len(sentences))
    rules: list[Rule] = []

    for idx, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue

        modality = _detect_modality(sentence)
        rule_type = _detect_rule_type(sentence)
        absoluteness = _compute_absoluteness(sentence)
        negated = _has_negation(sentence)
        condition = _extract_condition(sentence)
        keywords = _extract_keywords(sentence)

        # Skip purely descriptive sentences with no normative signal
        has_signal = (
            modality != Modality.UNKNOWN
            or rule_type not in (RuleType.UNKNOWN,)
            or negated
        )
        if not has_signal:
            continue

        rule = Rule(
            text=sentence,
            sentence_index=idx,
            modality=modality,
            rule_type=rule_type,
            absoluteness=absoluteness,
            negated=negated,
            condition=condition,
            keywords=keywords,
        )
        rules.append(rule)

    logger.debug(
        "parse: extracted %d rules from %d sentences", len(rules), len(sentences)
    )
    return rules


def parse_file(path: str) -> list[Rule]:
    """Read a file and parse its contents as a system prompt."""
    with open(path, "r", encoding="utf-8") as fh:
        return parse(fh.read())
