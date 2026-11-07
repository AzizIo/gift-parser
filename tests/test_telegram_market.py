from decimal import Decimal
from types import SimpleNamespace

from telethon import functions

from app.models import Seller
from app.sources.telegram_market import TelegramMarketSource


def test_telethon_resale_request_is_available_and_constructible():
    request = functions.payments.GetResaleStarGiftsRequest(
        gift_id=123456789,
        offset="",
        limit=100,
    )
    assert request.gift_id == 123456789
    assert request.offset == ""
    assert request.limit == 100


def test_telethon_gift_catalog_request_is_available_and_constructible():
    request = functions.payments.GetStarGiftsRequest(hash=0)
    assert request.hash == 0


def test_stars_amount_conversion():
    stars = SimpleNamespace(amount=980, nanos=0)
    assert TelegramMarketSource._format_prices([stars]) == ["980 Stars"]


def test_stars_amount_with_nanos_conversion():
    stars = SimpleNamespace(amount=12, nanos=500_000_000)
    assert TelegramMarketSource._format_prices([stars]) == ["12.5 Stars"]


def test_ton_nanograms_conversion():
    class StarsTonAmount:
        amount = 1_257_000_000

    ton = StarsTonAmount()
    assert TelegramMarketSource._format_prices([ton]) == ["1.257 TON"]


def test_seller_peer_is_resolved_only_from_returned_telegram_peer():
    gift = SimpleNamespace(
        owner_id=SimpleNamespace(user_id=7654321),
        owner_name=None,
        owner_address=None,
    )
    user = SimpleNamespace(
        id=7654321,
        username="seller_example",
        first_name="Gift",
        last_name="Seller",
    )
    response = SimpleNamespace(users=[user], chats=[])

    seller = TelegramMarketSource._resolve_seller(gift, response)

    assert seller.telegram_id == 7654321
    assert seller.username == "seller_example"
    assert seller.profile_url == "https://t.me/seller_example"
    assert seller.confidence == "telegram_peer"


def test_hidden_owner_name_does_not_get_guessed_as_account():
    gift = SimpleNamespace(owner_id=None, owner_name="Hidden Seller", owner_address=None)
    response = SimpleNamespace(users=[], chats=[])

    seller = TelegramMarketSource._resolve_seller(gift, response)

    assert seller.display_name == "Hidden Seller"
    assert seller.telegram_id is None
    assert seller.username is None
    assert seller.profile_url is None
    assert seller.confidence == "name_only"


def test_wallet_owner_is_not_misrepresented_as_telegram_account():
    gift = SimpleNamespace(owner_id=None, owner_name=None, owner_address="EQ_wallet_address")
    response = SimpleNamespace(users=[], chats=[])

    seller = TelegramMarketSource._resolve_seller(gift, response)

    assert seller.wallet_address == "EQ_wallet_address"
    assert seller.telegram_id is None
    assert seller.username is None
    assert seller.confidence == "wallet_only"


def test_listing_parser_extracts_gift_attributes_and_price():
    class StarGiftAttributeModel:
        name = "Ronaldo"
        rarity = SimpleNamespace(permille=10)

    class StarGiftAttributeBackdrop:
        name = "Silver Blue"
        rarity = SimpleNamespace(permille=15)

    class StarGiftAttributePattern:
        name = "Golden Scarab"
        rarity = SimpleNamespace(permille=4)

    class StarsTonAmount:
        amount = 12_570_000_000

    gift = SimpleNamespace(
        slug="InputKey-84682",
        num=84682,
        title="Input Key",
        resell_amount=[StarsTonAmount()],
        attributes=[
            StarGiftAttributeModel(),
            StarGiftAttributeBackdrop(),
            StarGiftAttributePattern(),
        ],
        owner_id=None,
        owner_name="Private account",
        owner_address=None,
        id=987654,
    )
    response = SimpleNamespace(users=[], chats=[])

    source = TelegramMarketSource()
    listing = source._to_listing(gift, response)

    assert listing is not None
    assert listing.gift_ref == "InputKey-84682"
    assert listing.gift_url == "https://t.me/nft/InputKey-84682"
    assert listing.title == "Input Key #84682"
    assert listing.price == Decimal("12.57")
    assert listing.currency == "TON"
    assert listing.price_labels == ("12.57 TON",)
    assert listing.model == "Ronaldo 1%"
    assert listing.backdrop == "Silver Blue 1.5%"
    assert listing.pattern == "Golden Scarab 0.4%"
    assert listing.seller.confidence == "name_only"
