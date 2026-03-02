"""Async Telegram Bot API client."""

from __future__ import annotations

import httpx


class TelegramError(Exception):
    """Raised when the Telegram API returns an error response."""

    def __init__(self, description: str, error_code: int) -> None:
        super().__init__(f"Telegram API error {error_code}: {description}")
        self.error_code = error_code
        self.description = description


class TelegramBot:
    """Minimal async client for the Telegram Bot API."""

    def __init__(self, token: str) -> None:
        self._base = f"https://api.telegram.org/bot{token}"

    async def _call(self, method: str, **params: object) -> object:
        """POST a Telegram Bot API method and return the result field."""
        payload = {k: v for k, v in params.items() if v is not None}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self._base}/{method}", json=payload)
            data = resp.json()
        if not data.get("ok"):
            raise TelegramError(
                data.get("description", "Unknown error"),
                data.get("error_code", resp.status_code),
            )
        return data["result"]

    # ---- informational -------------------------------------------------------

    async def get_me(self) -> dict:
        return await self._call("getMe")  # type: ignore[return-value]

    async def get_chat(self, chat_id: int | str) -> dict:
        return await self._call("getChat", chat_id=chat_id)  # type: ignore[return-value]

    async def get_chat_member_count(self, chat_id: int | str) -> int:
        return await self._call("getChatMemberCount", chat_id=chat_id)  # type: ignore[return-value]

    # ---- sending -------------------------------------------------------------

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str | None = None,
        disable_web_page_preview: bool | None = None,
        reply_to_message_id: int | None = None,
    ) -> dict:
        return await self._call(  # type: ignore[return-value]
            "sendMessage",
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_photo(
        self,
        chat_id: int | str,
        photo: str,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> dict:
        return await self._call(  # type: ignore[return-value]
            "sendPhoto",
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            parse_mode=parse_mode,
        )

    async def send_document(
        self,
        chat_id: int | str,
        document: str,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> dict:
        return await self._call(  # type: ignore[return-value]
            "sendDocument",
            chat_id=chat_id,
            document=document,
            caption=caption,
            parse_mode=parse_mode,
        )

    async def send_location(
        self,
        chat_id: int | str,
        latitude: float,
        longitude: float,
        horizontal_accuracy: float | None = None,
    ) -> dict:
        return await self._call(  # type: ignore[return-value]
            "sendLocation",
            chat_id=chat_id,
            latitude=latitude,
            longitude=longitude,
            horizontal_accuracy=horizontal_accuracy,
        )

    async def send_poll(
        self,
        chat_id: int | str,
        question: str,
        options: list[str],
        is_anonymous: bool = True,
        allows_multiple_answers: bool = False,
    ) -> dict:
        return await self._call(  # type: ignore[return-value]
            "sendPoll",
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=is_anonymous,
            allows_multiple_answers=allows_multiple_answers,
        )

    # ---- editing / deleting --------------------------------------------------

    async def edit_message_text(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        parse_mode: str | None = None,
    ) -> dict:
        return await self._call(  # type: ignore[return-value]
            "editMessageText",
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
        )

    async def delete_message(self, chat_id: int | str, message_id: int) -> bool:
        return await self._call(  # type: ignore[return-value]
            "deleteMessage",
            chat_id=chat_id,
            message_id=message_id,
        )
