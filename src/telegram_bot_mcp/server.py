"""FastMCP server — exposes Telegram Bot API as MCP tools."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastmcp import FastMCP

from .auth import create_auth
from .telegram import TelegramBot, TelegramError

# ---------------------------------------------------------------------------
# Chat discovery persistence
# ---------------------------------------------------------------------------

_CHAT_STORE_PATH = Path(
    os.getenv(
        "CHAT_STORE_PATH",
        Path.home() / ".local/share/fastmcp/chats.json",
    )
)


def _load_store() -> dict:
    """Load chat store from disk, returning empty structure on missing/corrupt file."""
    try:
        return json.loads(_CHAT_STORE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"next_offset": None, "chats": {}}


def _save_store(store: dict) -> None:
    _CHAT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CHAT_STORE_PATH.write_text(json.dumps(store, indent=2))


def _parse_known_chats_env() -> dict[str, dict]:
    """Parse KNOWN_CHATS env var: 'Name=chat_id,Name2=chat_id2'."""
    raw = os.getenv("KNOWN_CHATS", "")
    result: dict[str, dict] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if "=" not in entry:
            continue
        name, _, chat_id_str = entry.partition("=")
        try:
            chat_id = int(chat_id_str.strip())
            result[str(chat_id)] = {
                "chat_id": chat_id,
                "name": name.strip(),
                "type": "unknown",
                "username": None,
                "source": "static",
            }
        except ValueError:
            pass
    return result


def _extract_chat(update: dict) -> dict | None:
    """Extract chat info from any update type."""
    for key in ("message", "channel_post", "edited_message", "edited_channel_post",
                "my_chat_member", "chat_member"):
        payload = update.get(key)
        if payload:
            chat = payload.get("chat")
            if chat:
                return chat
    return None

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server & bot initialisation
# ---------------------------------------------------------------------------

mcp = FastMCP(name="telegram-bot-mcp", auth=create_auth())
_bot: TelegramBot | None = None


def _get_bot() -> TelegramBot:
    global _bot
    if _bot is None:
        token = os.environ["TELEGRAM_BOT_TOKEN"]
        _bot = TelegramBot(token)
    return _bot


def _wrap(coro):
    """Uniform error handling: re-raise TelegramError as a descriptive string."""

    async def _inner(*args, **kwargs):
        try:
            return await coro(*args, **kwargs)
        except TelegramError as exc:
            raise RuntimeError(str(exc)) from exc

    return _inner


# ---------------------------------------------------------------------------
# Tools — Phase 1
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_me() -> dict:
    """Return basic information about the bot (id, username, name, etc.)."""
    return await _wrap(_get_bot().get_me)()


@mcp.tool()
async def get_chat(chat_id: str) -> dict:
    """Return information about a chat (group, channel, or private).

    Args:
        chat_id: Unique identifier for the target chat or username
                 (e.g. "@channelusername" or a numeric id like "-1001234567890").
    """
    return await _wrap(_get_bot().get_chat)(chat_id)


@mcp.tool()
async def get_chat_member_count(chat_id: str) -> int:
    """Return the number of members in a chat.

    Args:
        chat_id: Unique identifier for the target chat or username.
    """
    return await _wrap(_get_bot().get_chat_member_count)(chat_id)


@mcp.tool()
async def send_message(
    chat_id: str,
    text: str,
    parse_mode: str | None = None,
    disable_web_page_preview: bool | None = None,
    reply_to_message_id: int | None = None,
) -> dict:
    """Send a text message to a Telegram chat.

    Args:
        chat_id: Target chat id or @username.
        text: Message text (up to 4096 characters).
        parse_mode: "HTML", "Markdown", or "MarkdownV2" for rich formatting.
        disable_web_page_preview: Disable link previews in the message.
        reply_to_message_id: If set, the message will reply to this message id.
    """
    return await _wrap(_get_bot().send_message)(
        chat_id,
        text,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
        reply_to_message_id=reply_to_message_id,
    )


@mcp.tool()
async def send_photo(
    chat_id: str,
    photo: str,
    caption: str | None = None,
    parse_mode: str | None = None,
) -> dict:
    """Send a photo to a Telegram chat.

    Args:
        chat_id: Target chat id or @username.
        photo: HTTP(S) URL of the photo or a Telegram file_id.
        caption: Optional caption (up to 1024 characters).
        parse_mode: Formatting for the caption ("HTML", "Markdown", etc.).
    """
    return await _wrap(_get_bot().send_photo)(
        chat_id, photo, caption=caption, parse_mode=parse_mode
    )


@mcp.tool()
async def send_document(
    chat_id: str,
    document: str,
    caption: str | None = None,
    parse_mode: str | None = None,
) -> dict:
    """Send a file/document to a Telegram chat.

    Args:
        chat_id: Target chat id or @username.
        document: HTTP(S) URL of the file or a Telegram file_id.
        caption: Optional caption (up to 1024 characters).
        parse_mode: Formatting for the caption ("HTML", "Markdown", etc.).
    """
    return await _wrap(_get_bot().send_document)(
        chat_id, document, caption=caption, parse_mode=parse_mode
    )


@mcp.tool()
async def send_location(
    chat_id: str,
    latitude: float,
    longitude: float,
    horizontal_accuracy: float | None = None,
) -> dict:
    """Send a geographic location to a Telegram chat.

    Args:
        chat_id: Target chat id or @username.
        latitude: Latitude of the location.
        longitude: Longitude of the location.
        horizontal_accuracy: Radius of uncertainty in metres (0–1500).
    """
    return await _wrap(_get_bot().send_location)(
        chat_id,
        latitude,
        longitude,
        horizontal_accuracy=horizontal_accuracy,
    )


@mcp.tool()
async def send_poll(
    chat_id: str,
    question: str,
    options: list[str],
    is_anonymous: bool = True,
    allows_multiple_answers: bool = False,
) -> dict:
    """Send a poll to a Telegram chat.

    Args:
        chat_id: Target chat id or @username.
        question: Poll question (1–300 characters).
        options: List of 2–10 answer options (each 1–100 characters).
        is_anonymous: True if the poll should be anonymous (default).
        allows_multiple_answers: True to allow multiple answers.
    """
    return await _wrap(_get_bot().send_poll)(
        chat_id,
        question,
        options,
        is_anonymous=is_anonymous,
        allows_multiple_answers=allows_multiple_answers,
    )


@mcp.tool()
async def edit_message_text(
    chat_id: str,
    message_id: int,
    text: str,
    parse_mode: str | None = None,
) -> dict:
    """Edit the text of an existing message.

    Args:
        chat_id: Chat id or @username of the chat containing the message.
        message_id: Identifier of the message to edit.
        text: New text content (up to 4096 characters).
        parse_mode: Formatting ("HTML", "Markdown", etc.).
    """
    return await _wrap(_get_bot().edit_message_text)(
        chat_id, message_id, text, parse_mode=parse_mode
    )


@mcp.tool()
async def delete_message(chat_id: str, message_id: int) -> bool:
    """Delete a message from a chat.

    Args:
        chat_id: Chat id or @username containing the message.
        message_id: Identifier of the message to delete.
    """
    return await _wrap(_get_bot().delete_message)(chat_id, message_id)


@mcp.tool()
async def list_chats() -> dict:
    """List all known chats the bot can send messages to.

    Combines two sources:
    - **Persistent discovery**: fetches new Telegram updates, extracts chats, and
      saves them to disk. Subsequent calls return the cached list instantly plus
      any newly discovered chats.
    - **Static config**: chats defined via the KNOWN_CHATS environment variable
      (format: "Name=chat_id,Name2=chat_id2") are always included.

    Returns a dict with:
    - chats: list of {chat_id, name, type, username, source}
    - hint: what to tell the user if their desired chat is not in the list

    Use the chat_id value with send_message and other tools.
    If the desired chat is missing, communicate the hint to the user and call
    list_chats again after they have followed the instructions.
    """
    store = _load_store()

    # Fetch new updates from Telegram and merge into store
    try:
        updates = await _get_bot().get_updates(offset=store["next_offset"], limit=100)
        new_max_id: int | None = None
        for u in updates:
            update_id: int = u["update_id"]
            if new_max_id is None or update_id > new_max_id:
                new_max_id = update_id
            chat = _extract_chat(u)
            if chat is None:
                continue
            key = str(chat["id"])
            name = (
                chat.get("title")
                or f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip()
                or chat.get("username")
                or key
            )
            store["chats"][key] = {
                "chat_id": chat["id"],
                "name": name,
                "type": chat.get("type", "unknown"),
                "username": chat.get("username"),
                "source": "discovered",
            }
        if new_max_id is not None:
            store["next_offset"] = new_max_id + 1
        _save_store(store)
    except Exception as exc:
        logger.warning("getUpdates failed, returning cached chats: %s", exc)

    # Merge static entries (static wins for same chat_id)
    merged = {**store["chats"], **_parse_known_chats_env()}
    chats = sorted(merged.values(), key=lambda c: c["name"].lower())
    return {
        "chats": chats,
        "hint": (
            "If the desired chat is not listed: ask the person to open Telegram and "
            "send /start to this bot. Then call list_chats again — they will appear automatically."
        ),
    }
