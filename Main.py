import logging
import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

AFFILIATE_PID = "1782033410"

_URL_RE = re.compile(r"https?://[^\s<>'\"()]")
_ALIBABA_HOST_RE = re.compile(
    r"(?:^|\.)(?:alibaba\.com|aliexpress\.[a-z]+)$",
    re.IGNORECASE,
)
_TRAILING_PUNCTUATION = ".,;:!?"


def _is_alibaba_host(host: str) -> bool:
    return bool(_ALIBABA_HOST_RE.search(host or ""))


def to_affiliate_link(url: str) -> str | None:
    """Return the affiliate version of an Alibaba or AliExpress URL, or None."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if not _is_alibaba_host(parts.hostname or ""):
        return None

    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if query.get("pid") == AFFILIATE_PID:
        return url

    query["pid"] = AFFILIATE_PID
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def convert_links(text: str) -> list[str]:
    converted = []
    for raw in _URL_RE.findall(text or ""):
        cleaned_raw = raw.rstrip(_TRAILING_PUNCTUATION)
        affiliate = to_affiliate_link(cleaned_raw)
        if affiliate:
            converted.append(affiliate)

    seen = set()
    unique = []
    for link in converted:
        if link not in seen:
            seen.add(link)
            unique.append(link)
    return unique


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Send me an Alibaba or AliExpress link!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    text = message.text or message.caption or ""
    links = convert_links(text)
    if not links:
        return
    body = "\n".join(links)
    await message.reply_text(
        f"Affiliate link(s):\n{body}",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN environment variable not set")

    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT | filters.CAPTION, handle_message)
    )

    logger.info("Bot starting")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
