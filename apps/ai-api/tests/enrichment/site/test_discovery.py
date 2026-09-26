"""Finding a supplier's own website among search results, and which of its pages to read."""
from __future__ import annotations

from ai_api.enrichment.site.discovery import find_website, name_keys, pages_to_crawl


def _results(*hrefs: str) -> list[dict]:
    return [{"title": "", "body": "", "href": href} for href in hrefs]


def test_legal_forms_and_punctuation_are_dropped_from_the_name():
    assert name_keys("Dansk Kaffe ApS") == ["dansk", "danskkaffe"]
    assert name_keys("Google Cloud EMEA Limited") == [
        "google", "googlecloud", "googlecloudemea",
    ]


def test_danish_letters_are_spelled_as_domains_spell_them():
    assert name_keys("Bølgen & Blæst A/S") == [
        "boelgen", "boelgenblaest",
    ]


def test_the_own_domain_is_chosen_over_a_directory():
    results = _results(
        "https://www.proff.dk/firma/dansk-kaffe-aps/123",
        "https://danskkaffe.dk/om-os",
    )

    assert find_website("Dansk Kaffe ApS", results) == "https://danskkaffe.dk/"


def test_a_hyphenated_domain_matches():
    results = _results("https://www.dansk-kaffe.dk/")

    assert find_website("Dansk Kaffe ApS", results) == "https://www.dansk-kaffe.dk/"


def test_a_first_word_domain_matches():
    results = _results("https://cloud.google.com/products")

    assert find_website("Google Cloud EMEA Limited", results) == "https://cloud.google.com/"


def test_a_short_acronym_matches_exactly():
    results = _results("https://www.dsb.dk/rejseplan")

    assert find_website("DSB", results) == "https://www.dsb.dk/"


def test_a_namesake_is_not_taken_for_the_supplier():
    results = _results("https://danskebank.dk/", "https://kaffe.dk/")

    assert find_website("Dansk Kaffe ApS", results) is None


def test_a_social_profile_is_never_the_website():
    results = _results(
        "https://www.linkedin.com/company/dansk-kaffe",
        "https://danskkaffe.facebook.com/",
    )

    assert find_website("Dansk Kaffe ApS", results) is None


def test_a_result_without_a_link_is_skipped():
    results = [{"title": "Dansk Kaffe", "body": "coffee"}, *_results("https://danskkaffe.dk/")]

    assert find_website("Dansk Kaffe ApS", results) == "https://danskkaffe.dk/"


def test_a_name_with_no_words_finds_nothing():
    assert find_website("A/S", _results("https://as.dk/")) is None


def test_pages_stay_on_the_site():
    links = [
        "https://danskkaffe.dk/om-os",
        "https://facebook.com/danskkaffe",
        "https://shop.example.com/produkter",
    ]

    assert pages_to_crawl("https://danskkaffe.dk/", links, limit=3) == [
        "https://danskkaffe.dk/om-os",
    ]


def test_pages_about_the_company_come_first_and_are_capped():
    links = [
        "https://danskkaffe.dk/blog/nyhed-1",
        "https://danskkaffe.dk/kontakt",
        "https://danskkaffe.dk/produkter",
        "https://danskkaffe.dk/about-us",
        "https://danskkaffe.dk/ydelser",
    ]

    assert pages_to_crawl("https://danskkaffe.dk/", links, limit=2) == [
        "https://danskkaffe.dk/about-us",
        "https://danskkaffe.dk/produkter",
    ]


def test_only_pages_about_the_company_are_read():
    links = ["https://danskkaffe.dk/blog/nyhed-1", "https://danskkaffe.dk/kontakt"]

    assert pages_to_crawl("https://danskkaffe.dk/", links, limit=3) == []


def test_the_home_page_and_repeats_are_not_listed_again():
    links = [
        "https://danskkaffe.dk/",
        "https://danskkaffe.dk/om-os#team",
        "https://danskkaffe.dk/om-os",
    ]

    assert pages_to_crawl("https://danskkaffe.dk/", links, limit=3) == [
        "https://danskkaffe.dk/om-os",
    ]
