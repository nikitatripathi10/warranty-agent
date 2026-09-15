"""
Smoke tests for the three enhancements added in this milestone.

Run with:
    venv\\Scripts\\pytest tests/test_enhancements.py -v
"""

import pathlib
from decimal import Decimal


# -- Enhancement 1: Gmail query coverage ------------------------------------

def test_gmail_query_contains_all_new_domains():
    from app.services.gmail_client import GMAIL_SEARCH_QUERY
    for domain in [
        "amazon.in", "flipkart.com", "myntra.com", "meesho.com",
        "ajio.com", "jiomart.com", "blinkit.com", "zeptonow.com", "swiggy.com",
    ]:
        assert domain in GMAIL_SEARCH_QUERY, f"Missing domain in Gmail query: {domain}"


# -- Enhancement 1: Meesho regex extractor ----------------------------------

MEESHO_SAMPLE = (
    "Hi Priya,\n"
    "Your Meesho order has been confirmed!\n"
    "Order ID: 987654321012\n"
    "Product Name: Campus Women Running Shoes\n"
    "Order Date: 05-08-2025\n"
    "Order Total: Rs. 1,299\n"
    "7 days return policy applicable.\n"
)


def test_extract_meesho_basic():
    from app.services.extractor_regex import extract_meesho
    result = extract_meesho(MEESHO_SAMPLE)
    assert result is not None
    assert result.retailer == "Meesho"
    assert result.price == Decimal("1299")
    assert result.return_window_days == 7
    assert result.confidence in ("high", "medium")


def test_extract_meesho_returns_none_for_non_meesho():
    from app.services.extractor_regex import extract_meesho
    result = extract_meesho("Your Amazon order #123-4567890-1234567 has been placed.")
    assert result is None


# -- Enhancement 1: Ajio regex extractor ------------------------------------

AJIO_SAMPLE = (
    "Hello Rohan,\n"
    "Your Ajio order has been placed successfully.\n"
    "Order ID: FN20250912345678\n"
    "Product Name: HM Slim Fit Chinos (Beige)\n"
    "Order Date: 12/09/2025\n"
    "Order Total: Rs. 2,499\n"
    "30 days return policy.\n"
)


def test_extract_ajio_basic():
    from app.services.extractor_regex import extract_ajio
    result = extract_ajio(AJIO_SAMPLE)
    assert result is not None
    assert result.retailer == "Ajio"
    assert result.price == Decimal("2499")
    assert result.return_window_days == 30
    assert result.confidence in ("high", "medium")


def test_extract_ajio_returns_none_for_non_ajio():
    from app.services.extractor_regex import extract_ajio
    result = extract_ajio("Your Flipkart order OD12345678901234567 has shipped.")
    assert result is None


# -- Enhancement 1: run_regex_pass hint routing -----------------------------

def test_run_regex_pass_routes_meesho():
    from app.services.extractor_regex import run_regex_pass
    result = run_regex_pass(MEESHO_SAMPLE, hint="meesho")
    assert result.retailer == "Meesho"


def test_run_regex_pass_routes_ajio():
    from app.services.extractor_regex import run_regex_pass
    result = run_regex_pass(AJIO_SAMPLE, hint="ajio")
    assert result.retailer == "Ajio"


# -- Enhancement 2: LLM prompt multilingual ---------------------------------

def test_llm_prompt_has_multilingual_rule():
    from app.services.extractor_llm import _SYSTEM_PROMPT
    assert "MULTILINGUAL" in _SYSTEM_PROMPT
    assert "Hindi" in _SYSTEM_PROMPT
    assert "Hinglish" in _SYSTEM_PROMPT


def test_llm_prompt_has_hindi_few_shot():
    from app.services.extractor_llm import _FEW_SHOT_EXAMPLES
    assert "EXAMPLE 4" in _FEW_SHOT_EXAMPLES
    assert "Samsung Galaxy Buds2 Pro" in _FEW_SHOT_EXAMPLES


# -- Enhancement 3: household_member in model -------------------------------

def test_purchase_model_has_household_member():
    from app.models import Purchase
    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(Purchase)
    col_names = [c.key for c in mapper.mapper.column_attrs]
    assert "household_member" in col_names


def test_household_member_is_nullable():
    from app.models import Purchase
    from sqlalchemy import inspect as sa_inspect
    mapper = sa_inspect(Purchase)
    col = mapper.mapper.columns["household_member"]
    assert col.nullable is True


# -- Enhancement 3: migration file chain ------------------------------------

def test_migration_0002_chain():
    import importlib.util
    p = (
        pathlib.Path(__file__).parent.parent
        / "app" / "alembic" / "versions" / "0002_add_household_member.py"
    )
    assert p.exists(), "Migration 0002 not found"
    spec = importlib.util.spec_from_file_location("mig0002", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.revision == "0002"
    assert mod.down_revision == "0001"
