"""Reusing a categorization answered before for the same question and candidates."""
from __future__ import annotations

from functools import lru_cache

from sqlmodel import Session, select

from ..persistence import CategorizationCache
from ..sync.cache import question_sample, tree_hash
from ..sync.categorizer import Category, CategoryMatch
from ..sync.llm_categorizer import CategorizerUnavailable


@lru_cache(maxsize=256)
def hash_for(offered: tuple[Category, ...]) -> str:
    """The candidate set's digest, memoised per distinct set."""
    return tree_hash(offered)


def cached_answer(
    session: Session, question_key: str, offered_hash: str
) -> CategorizationCache | None:
    """The stored answer to this question against this candidate set, if any."""
    return session.exec(
        select(CategorizationCache).where(
            CategorizationCache.question_key == question_key,
            CategorizationCache.tree_hash == offered_hash,
        )
    ).first()


def match_from_cache(row: CategorizationCache, offered: list[Category]) -> CategoryMatch:
    """Rebuild an answer from a cached row, against the set it was given for."""
    node = next((c for c in offered if c.node_id == row.spend_category_id), None)
    if node is None:
        raise CategorizerUnavailable(
            "a cached answer names a category that is no longer offered"
        )
    return CategoryMatch(
        matched=True,
        spend_category_id=node.node_id,
        account_code=node.code,
        account_name=node.name,
        level_1=node.level(0), level_2=node.level(1),
        level_3=node.level(2), level_4=node.level(3),
        confidence=row.confidence or 0.0,
        rationale=row.rationale or "",
        gt_level_1=None, gt_level_2=None, gt_level_3=None, gt_account_code=None,
    )


def remember_answer(
    session: Session,
    question_key: str,
    offered_hash: str,
    match: CategoryMatch,
    *,
    item_name: str | None,
    supplier_name: str | None,
    native_account_code: str | None,
) -> None:
    """Store a fresh model answer so the same question is not asked again."""
    session.add(CategorizationCache(
        question_key=question_key, tree_hash=offered_hash,
        spend_category_id=match.spend_category_id,
        confidence=match.confidence, rationale=match.rationale,
        question_sample=question_sample(item_name, supplier_name, native_account_code),
    ))
