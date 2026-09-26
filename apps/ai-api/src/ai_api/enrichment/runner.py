"""CLI for the vendor-enrichment stage."""
from __future__ import annotations

import argparse
import logging
from functools import partial

from sqlmodel import Session

from web_api.db.session import engine

from .. import config
from .site.crawler import crawl_site
from .site.fetch import fetch_site
from .supplier_profile import describe_supplier, locate_website
from .vendors import describe_vendors
from .websites import find_vendor_websites

logger = logging.getLogger("ai_api.enrichment")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Describe the suppliers the ledger only names, so a line can "
                    "be categorized from what its supplier actually sells.",
    )
    parser.add_argument(
        "--company-id", default=None,
        help="Work this company's suppliers first (the vendor row is global either way)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Describe at most this many suppliers, to pace a large backlog",
    )
    parser.add_argument(
        "--websites", action="store_true",
        help="Instead of describing suppliers, find the website of those already described "
             "that have none. Their descriptions are left as they are.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not config.VENDOR_ENRICHMENT_ENABLED:
        print(
            "VENDOR_ENRICHMENT_ENABLED is not set, so nothing was researched.\n"
            "This stage reaches the public web and writes to the global supplier\n"
            "catalog, so it is opt-in. Set it in .env to enable."
        )
        return 0

    if args.websites:
        return _find_websites(args.company_id, args.limit)

    if config.SUPPLIER_CRAWL_ENABLED:
        describe = partial(describe_supplier, crawl_fn=partial(crawl_site, fetch_site=fetch_site))
    else:
        print(
            "SUPPLIER_CRAWL_ENABLED is not set, so suppliers are described from search\n"
            "snippets only. Set it, after running `crawl4ai-setup`, to read their own websites."
        )
        describe = describe_supplier

    with Session(engine) as session:
        result = describe_vendors(
            session, company_id=args.company_id, limit=args.limit, describe=describe
        )

    if not result.considered:
        print("Every supplier in scope already has a description.")
        return 0

    print("\n=== vendor enrichment ===")
    for key, value in result.as_dict.items():
        print(f"{key}: {value}")
    return 0


def _find_websites(company_id: str | None, limit: int | None) -> int:
    if config.SUPPLIER_CRAWL_ENABLED:
        locate = partial(locate_website, crawl_fn=partial(crawl_site, fetch_site=fetch_site))
    else:
        print(
            "SUPPLIER_CRAWL_ENABLED is not set, so only websites the suppliers' invoices\n"
            "print are stored; a website found by search needs its site read to be confirmed."
        )
        locate = locate_website

    with Session(engine) as session:
        result = find_vendor_websites(session, company_id=company_id, limit=limit, locate=locate)

    if not result.considered:
        print("Every described supplier in scope already has a website.")
        return 0

    print("\n=== supplier websites ===")
    for key, value in result.as_dict.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
