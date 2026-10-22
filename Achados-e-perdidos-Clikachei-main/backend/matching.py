"""
Motor de Validação de Reivindicações.

Compara as respostas do questionário com o gabarito sigiloso do item e produz
um score ponderado de 0 a 1. O desafio de projeto aqui é equilibrar duas forças
opostas:

  * **Rigor** — um fraudador não pode acertar com descrições genéricas.
  * **Tolerância** — o dono legítimo escreve "azul escuro" onde o gabarito diz
    "azul-marinho", erra acentos, usa maiúsculas ou singular/plural.

A estratégia é uma cascata de comparadores, do mais estrito ao mais flexível:
normalização → igualdade → sinônimos → contenção → similaridade de tokens →
similaridade de caracteres (difflib). Campos numéricos usam tolerância relativa.

Campos marcados como `is_critical` (senha de desbloqueio, número de série)
funcionam como veto: errar um deles reprova a reivindicação inteira,
independentemente do score dos demais.

Este módulo é puro Python — não depende do Flask nem do banco — por isso as
constantes de configuração são recebidas como parâmetro em vez de importadas
de `current_app`, o que também facilita testar sem contexto de aplicação.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

# --------------------------------------------------------------------------- #
# Normalização
# --------------------------------------------------------------------------- #

_STOPWORDS = {
    "a", "as", "ao", "aos", "com", "da", "das", "de", "do", "dos", "e", "em",
    "na", "nas", "no", "nos", "o", "os", "para", "por", "um", "uma", "ums",
    "umas", "que", "eh", "e'", "sao", "esta", "meu", "minha", "seu", "sua",
    "tem", "possui", "cor", "marca", "modelo", "tipo",
}

_PUNCTUATION_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Reduz um texto à sua forma canônica comparável (sem acentos/pontuação)."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = _PUNCTUATION_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def tokenize(text: str) -> set[str]:
    tokens = {t for t in normalize(text).split() if len(t) > 1 and t not in _STOPWORDS}
    return tokens or set(normalize(text).split())


def _singularize(token: str) -> str:
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _token_similarity(a: str, b: str) -> float:
    tokens_a = {_singularize(t) for t in tokenize(a)}
    tokens_b = {_singularize(t) for t in tokenize(b)}
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _char_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


# --------------------------------------------------------------------------- #
# Resultado
# --------------------------------------------------------------------------- #


@dataclass
class AttributeScore:
    attribute_id: int
    question: str
    given: str
    score: float
    weight: int
    is_critical: bool
    matched: bool

    def as_dict(self) -> dict:
        return {
            "attribute_id": self.attribute_id,
            "question": self.question,
            "given": self.given,
            "score": round(self.score, 3),
            "weight": self.weight,
            "is_critical": self.is_critical,
            "matched": self.matched,
        }


@dataclass
class ValidationResult:
    score: float
    status: str  # approved | rejected | pending_review
    breakdown: list[AttributeScore] = field(default_factory=list)
    critical_failure: bool = False

    def breakdown_as_dicts(self) -> list[dict]:
        return [entry.as_dict() for entry in self.breakdown]


# --------------------------------------------------------------------------- #
# Comparadores por tipo de campo
# --------------------------------------------------------------------------- #


def _score_number(given: str, expected: str, tolerance: float) -> float:
    def parse(value: str) -> float | None:
        match = re.search(r"-?\d+(?:[.,]\d+)?", str(value).replace(" ", ""))
        if not match:
            return None
        return float(match.group().replace(",", "."))

    a, b = parse(given), parse(expected)
    if a is None or b is None:
        return 0.0
    if a == b:
        return 1.0

    scale = max(abs(b), 1e-9)
    deviation = abs(a - b) / scale
    if deviation <= tolerance:
        return 1.0
    if deviation <= tolerance * 2:
        return 0.5
    return 0.0


def _score_text(given: str, expected: str, alternatives: list[str]) -> float:
    norm_given = normalize(given)
    norm_expected = normalize(expected)

    if not norm_given:
        return 0.0
    if norm_given == norm_expected:
        return 1.0

    for alternative in alternatives:
        norm_alt = normalize(alternative)
        if norm_alt and (norm_given == norm_alt or norm_alt in norm_given):
            return 1.0

    if len(norm_expected) >= 4 and norm_expected in norm_given:
        return 0.95
    if len(norm_given) >= 4 and norm_given in norm_expected:
        return 0.85

    similarity = max(_token_similarity(given, expected), _char_similarity(given, expected))
    if similarity >= 0.85:
        return 1.0
    if similarity >= 0.70:
        return 0.75
    if similarity >= 0.55:
        return 0.45
    if similarity >= 0.40:
        return 0.20
    return 0.0


def score_attribute(attribute: dict, given: str) -> float:
    """Aplica o comparador adequado ao `field_type` do atributo."""
    given = (given or "").strip()
    if not given:
        return 0.0

    field_type = attribute.get("field_type", "text")
    expected = attribute.get("expected_answer", "")

    if field_type == "number":
        return _score_number(given, expected, float(attribute.get("tolerance", 0.1)))

    if field_type == "choice":
        alternatives = attribute.get("alternatives") or []
        candidates = [normalize(expected), *(normalize(a) for a in alternatives)]
        return 1.0 if normalize(given) in candidates else 0.0

    return _score_text(given, expected, attribute.get("alternatives") or [])


# --------------------------------------------------------------------------- #
# API do motor
# --------------------------------------------------------------------------- #


def validate_claim(
    attributes: list[dict],
    answers: dict[str, str],
    *,
    auto_approve_threshold: float,
    manual_review_threshold: float,
    critical_field_threshold: float,
) -> ValidationResult:
    """
    Avalia um questionário completo.

    Os limiares são recebidos como parâmetro (vindos de `current_app.config`
    na camada Service) para manter este módulo livre de qualquer dependência
    do Flask — pode ser testado isoladamente com valores fixos.
    """
    if not attributes:
        return ValidationResult(score=0.0, status="rejected")

    breakdown: list[AttributeScore] = []
    critical_failure = False
    total_weight = 0
    weighted_sum = 0.0

    for attribute in attributes:
        attribute_id = attribute["id"]
        given = answers.get(str(attribute_id), "")
        score = score_attribute(attribute, given)
        weight = int(attribute.get("weight", 1))
        is_critical = bool(attribute.get("is_critical", 0))

        total_weight += weight
        weighted_sum += score * weight

        if is_critical and score < critical_field_threshold:
            critical_failure = True

        breakdown.append(
            AttributeScore(
                attribute_id=attribute_id, question=attribute["question"], given=given,
                score=score, weight=weight, is_critical=is_critical, matched=score >= 0.75,
            )
        )

    final_score = weighted_sum / total_weight if total_weight else 0.0

    if critical_failure:
        status = "rejected"
    elif final_score >= auto_approve_threshold:
        status = "approved"
    elif final_score >= manual_review_threshold:
        status = "pending_review"
    else:
        status = "rejected"

    return ValidationResult(
        score=final_score, status=status, breakdown=breakdown, critical_failure=critical_failure,
    )
