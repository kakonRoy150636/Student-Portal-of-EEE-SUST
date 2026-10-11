"""Explicit academic-term ordering shared by SQL reads and Python mutations."""

from sqlalchemy import ColumnElement, SQLColumnExpression, case, or_


ACADEMIC_TERMS = ("1-1", "1-2", "2-1", "2-2", "3-1", "3-2", "4-1", "4-2")
TERM_RANKS = {term: rank for rank, term in enumerate(ACADEMIC_TERMS)}


def is_term_eligible(current_term: str | None, target_term: str | None) -> bool:
    """Legacy unscoped semesters are open; scoped semesters require a valid peer or senior term."""
    if target_term is None:
        return True
    current_rank = TERM_RANKS.get(current_term) if current_term is not None else None
    target_rank = TERM_RANKS.get(target_term)
    return current_rank is not None and target_rank is not None and current_rank >= target_rank


def term_eligibility_clause(
    current_term: SQLColumnExpression[str | None],
    target_term: SQLColumnExpression[str | None],
) -> ColumnElement[bool]:
    """SQL equivalent of is_term_eligible, without comparing term strings.

    Unrecognized or missing terms rank as SQL NULL, so scoped comparisons fail
    closed even when both terms are invalid. Only a NULL target is unrestricted.
    """
    return or_(
        target_term.is_(None),
        case(TERM_RANKS, value=current_term) >= case(TERM_RANKS, value=target_term),
    )
