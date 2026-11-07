from html import escape
from app.models import GiftListing


SELLER_LABELS = {
    "telegram_peer": "Telegram API вернул ID владельца",
    "name_only": "Доступно только отображаемое имя",
    "wallet_only": "Доступен только TON-адрес",
    "unknown": "Аккаунт владельца не раскрыт",
}


def format_listing(listing: GiftListing) -> str:
    seller = listing.seller
    price = " · ".join(listing.price_labels) or (
        f"{listing.price} {listing.currency or ''}".strip()
        if listing.price is not None else "не указана"
    )
    lines = [
        "🎁 <b>Новое объявление Telegram NFT</b>",
        f"<b>{escape(listing.title)}</b>",
        f"💰 Цена: <b>{escape(price)}</b>",
        f"🎨 Модель: {escape(listing.model or '—')}",
        f"🖼 Фон: {escape(listing.backdrop or '—')}",
        f"🧩 Узор: {escape(listing.pattern or '—')}",
        "",
        "👤 <b>Продавец</b>",
        f"Имя: {escape(seller.display_name or 'Неизвестно') if seller else 'Неизвестно'}",
        f"Статус: {escape(SELLER_LABELS.get(seller.confidence, seller.confidence)) if seller else 'Неизвестно'}",
    ]
    if seller and seller.username:
        lines.append(f"Username: @{escape(seller.username.lstrip('@'))}")
    if seller and seller.telegram_id:
        lines.append(f"Telegram ID: <code>{seller.telegram_id}</code>")
    if seller and seller.wallet_address:
        lines.append(f"TON: <code>{escape(seller.wallet_address)}</code>")
    if seller and seller.profile_url:
        lines.append(
            f'<a href="{escape(seller.profile_url, quote=True)}">Профиль продавца</a>'
        )
    lines.append(f'<a href="{escape(listing.gift_url, quote=True)}">Открыть подарок</a>')
    return "\n".join(lines)
