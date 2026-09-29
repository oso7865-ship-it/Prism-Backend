"""Bound uploaded document JSON before parsing; never retain/log rejected input."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class DocumentBodyLimit:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or "/standards" not in path:
            await self.app(scope, receive, send)
            return
        messages: list[Message] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                return
            size += len(message.get("body", b""))
            if size > 256 * 1024:
                response = JSONResponse(
                    {
                        "error": {
                            "code": "DOCUMENT_TOO_LARGE",
                            "message": "문서 요청 크기를 줄여 주세요.",
                        }
                    },
                    status_code=413,
                    headers={"Cache-Control": "private, no-store"},
                )
                await response(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def bounded_receive() -> Message:
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, bounded_receive, send)
