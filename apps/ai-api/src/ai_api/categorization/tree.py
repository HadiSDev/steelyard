"""A company's spend tree as categorization candidates, and its retrieval index."""
from __future__ import annotations

import logging
from collections.abc import Callable

from sqlmodel import Session, select

from web_api.db.models import Company, SpendCategory

from .. import config as ai_config
from ..rag import indexer
from ..sync.categorizer import Category, build_candidates_from_tree

logger = logging.getLogger("ai_api.categorization")

Retriever = Callable[[str, int], list]


def _tree_nodes(session: Session, spend_tree_id: str) -> list[SpendCategory]:
    return list(
        session.exec(
            select(SpendCategory).where(SpendCategory.spend_tree_id == spend_tree_id)
        ).all()
    )


def tree_candidates(session: Session, company_id: str) -> list[Category] | None:
    """The candidate set for a company: the nodes of the tree it is assigned."""
    company = session.get(Company, company_id)
    if company is None or company.spend_tree_id is None:
        return None
    nodes = _tree_nodes(session, company.spend_tree_id)
    if not nodes:
        return None
    return build_candidates_from_tree(nodes)


def index_tree(session: Session, company_id: str) -> None:
    """Embed the company's tree for candidate retrieval."""
    if not ai_config.CATEGORY_RETRIEVAL_ENABLED:
        return
    company = session.get(Company, company_id)
    if company is None or company.spend_tree_id is None:
        return
    try:
        indexer.build_tree_index(_tree_nodes(session, company.spend_tree_id), company.spend_tree_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("    could not index the spend tree (%s); offering it whole", exc)


def _find_nothing(query: str, top_k: int) -> list:
    return []


def retriever_for(company: Company | None) -> Retriever:
    """A retrieval callable bound to this company's tree, or one that finds nothing."""
    if company is None or company.spend_tree_id is None:
        return _find_nothing
    if not ai_config.CATEGORY_RETRIEVAL_ENABLED:
        return _find_nothing
    spend_tree_id = company.spend_tree_id

    def retrieve(query: str, top_k: int) -> list:
        return indexer.retrieve_categories(query, spend_tree_id, top_k=top_k)

    return retrieve
