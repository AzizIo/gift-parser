from html import escape
from app.models import GiftListing


def format_listing(listing: GiftListing) -> str:
    seller = listing.seller
    price = f"{listing.price} {listing.currency or ''}".strip() if listing.price is not None else "не указана"
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
        f"Статус: {escape(seller.confidence) if seller else 'unknown'}",
    ]
    if seller and seller.username:
        lines.append(f"Username: @{escape(seller.username.lstrip('@'))}")
    if seller and seller.telegram_id:
        lines.append(f"Telegram ID: <code>{seller.telegram_id}</code>")
    if seller and seller.profile_url:
        lines.append(f'<a href="{escape(seller.profile_url, quote=True)}">Профиль продавца</a>')
    lines.append(f'<a href="{escape(listing.gift_url, quote=True)}">Открыть подарок</a>')
    return "\n".join(lines)
