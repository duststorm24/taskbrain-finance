from typing import Any

import certifi
from plaid import ApiClient, Configuration, Environment
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_recurring_get_request import TransactionsRecurringGetRequest
from plaid.model.transactions_recurring_get_request_options import TransactionsRecurringGetRequestOptions
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.transactions_sync_request_options import TransactionsSyncRequestOptions

from app.core.config import get_settings


def _client() -> plaid_api.PlaidApi:
    settings = get_settings()
    host = Environment.Sandbox if settings.plaid_env == "sandbox" else Environment.Production
    config = Configuration(
        host=host,
        api_key={
            "clientId": settings.plaid_client_id,
            "secret": settings.plaid_secret,
        },
    )
    config.ssl_ca_cert = certifi.where()
    return plaid_api.PlaidApi(ApiClient(config))


def _products(value: str) -> list[Products]:
    return [Products(product.strip()) for product in value.split(",") if product.strip()]


def create_link_token(user_id: str) -> str:
    settings = get_settings()
    request = LinkTokenCreateRequest(
        client_name="TaskBrain Finance",
        country_codes=[CountryCode("US")],
        language="en",
        user=LinkTokenCreateRequestUser(client_user_id=user_id),
        products=_products(settings.plaid_products),
        optional_products=_products(settings.plaid_optional_products),
    )
    response = _client().link_token_create(request)
    return response["link_token"]


def exchange_public_token_for_item(user_id: str, public_token: str) -> dict[str, Any]:
    del user_id
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = _client().item_public_token_exchange(request)
    return response.to_dict()


def get_accounts(access_token: str) -> dict[str, Any]:
    response = _client().accounts_get(AccountsGetRequest(access_token=access_token))
    return response.to_dict()


def get_transaction_updates(access_token: str, cursor: str | None) -> dict[str, Any]:
    added: list[dict[str, Any]] = []
    modified: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    next_cursor = cursor
    has_more = True
    transactions_update_status = None

    while has_more:
        request_payload: dict[str, Any] = {
            "access_token": access_token,
            "count": 500,
            "options": TransactionsSyncRequestOptions(include_personal_finance_category=True),
        }
        if next_cursor:
            request_payload["cursor"] = next_cursor
        request = TransactionsSyncRequest(**request_payload)
        response = _client().transactions_sync(request).to_dict()
        added.extend(response.get("added", []))
        modified.extend(response.get("modified", []))
        removed.extend(response.get("removed", []))
        next_cursor = response.get("next_cursor")
        has_more = bool(response.get("has_more"))
        transactions_update_status = response.get("transactions_update_status")

    return {
        "added": added,
        "modified": modified,
        "removed": removed,
        "next_cursor": next_cursor,
        "transactions_update_status": transactions_update_status,
    }


def get_recurring_transactions(access_token: str) -> dict[str, Any]:
    request = TransactionsRecurringGetRequest(
        access_token=access_token,
        options=TransactionsRecurringGetRequestOptions(include_personal_finance_category=True),
    )
    return _client().transactions_recurring_get(request).to_dict()
