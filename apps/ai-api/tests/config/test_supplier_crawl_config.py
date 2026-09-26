"""Crawling a supplier's site is opt-in and bounded."""
from __future__ import annotations

from ai_api import config


def test_crawling_is_off_unless_asked_for(monkeypatch):
    monkeypatch.delenv("SUPPLIER_CRAWL_ENABLED", raising=False)

    assert config._env_flag("SUPPLIER_CRAWL_ENABLED") is False


def test_the_crawl_is_bounded():
    assert config.SUPPLIER_CRAWL_MAX_PAGES >= 0
    assert config.SUPPLIER_CRAWL_TIMEOUT_S > 0
    assert config.SUPPLIER_CRAWL_MAX_CHARS > 0
