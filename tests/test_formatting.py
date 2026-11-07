from decimal import Decimal

from app.formatting import format_listing
from app.models import GiftListing, Seller


def test_format_listing_escapes_untrusted_text_and_keeps_links():
    listing = GiftListing(
        event_id="event-2",
        gift_ref="InputKey-84682",
        title="Input <Key> #84682",
        gift_url="https://t.me/nft/InputKey-84682",
        price=Decimal("12.57"),
        currency="TON",
        market="telegram",
        model="Ronaldo 1%",
        seller=Seller(
            display_name="<seller>",
            username="seller_test",
            telegram_id=123456,
            profile_url="https://t.me/seller_test",
            confidence="telegram_peer",
        ),
    )

    message = format_listing(listing)

    assert "Input &lt;Key&gt; #84682" in message
    assert "&lt;seller&gt;" in message
    assert "https://t.me/seller_test" in message
    assert "https://t.me/nft/InputKey-84682" in message
    assert "<seller>" not in message


def test_format_listing_without_owner_does_not_invent_profile():
    listing = GiftListing(
        event_id="event-3",
        gift_ref="InputKey-84682",
        title="Input Key #84682",
        gift_url="https://t.me/nft/InputKey-84682",
        price=None,
        currency=None,
        market="telegram",
        seller=Seller(display_name="Only a name", confidence="name_only"),
    )

    message = format_listing(listing)
    assert "Only a name" in message
    assert "Профиль продавца" not in message
    assert "Открыть подарок" in message
