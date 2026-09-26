"""Fake ERP connectors the integration endpoint tests register by type name."""
from __future__ import annotations

from web_api.connectors import ErpAuthError, register_connector
from web_api.connectors.base import CredentialField, ErpAccountData, ErpConnector


class FakeErpConnector(ErpConnector):
    """Reachable ERP whose account chart can grow between calls."""

    display_label = "Fake ERP"
    credential_fields = [
        CredentialField(name="base_url", label="Base URL", required=True),
        CredentialField(name="api_key", label="API key", secret=True),
    ]

    accounts: list[ErpAccountData] = [
        ErpAccountData(erp_account_code="6010", erp_account_name="Cloud", erp_account_type="expense", with_vat=True),
        ErpAccountData(erp_account_code="6020", erp_account_name="Software", erp_account_type="expense", with_vat=True),
    ]

    def authorize(self) -> str:
        return "t"

    def test_connection(self) -> bool:
        return True

    def fetch_accounts(self):
        return list(type(self).accounts)

    def fetch_vendors(self, since=None):
        return []

    def fetch_invoices(self, since=None):
        return []

    def fetch_entries(self, since=None, account_codes=None):
        return []

    def fetch_invoice_scan(self, voucher_id):
        return None

    def fetch_invoice_document(self, voucher_id):
        return None


class UnreachableErpConnector(FakeErpConnector):
    def test_connection(self) -> bool:
        raise RuntimeError("boom: unreachable")


class RejectingErpConnector(FakeErpConnector):
    def test_connection(self) -> bool:
        raise ErpAuthError("token tok_secret_123 expired")


class BrandedErpConnector(FakeErpConnector):
    """Declares the optional brand metadata, so the catalog can project it."""

    display_label = "Branded ERP"
    brand_slug = "branded"
    description = "An ERP with a face."
    docs_url = "https://example.invalid/docs"


register_connector("faketest", FakeErpConnector)
register_connector("faketest_bad", UnreachableErpConnector)
register_connector("faketest_branded", BrandedErpConnector)
register_connector("faketest_badauth", RejectingErpConnector)
