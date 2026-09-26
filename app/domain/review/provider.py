import asyncio
from typing import Protocol

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langsmith import tracing_context

from app.domain.review.harness import compose
from app.domain.review.policy import ReviewOutput
from app.shared.config.settings import Settings


class Provider(Protocol):
    model: str

    async def review(self, payload: str) -> tuple[str, int, int]: ...


class DeepSeekProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model: str = settings.deepseek_model

    async def review(self, payload: str) -> tuple[str, int, int]:
        if not self.settings.ai_enabled or not self.settings.deepseek_api_key:
            raise ValueError("AI_DISABLED")
        system, _ = compose(payload, ReviewOutput.model_json_schema())
        # No environment proxy, redirects, retry, streaming, tools or external traces.
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=60) as http:
            model = ChatDeepSeek(
                model_name=self.settings.deepseek_model,
                api_key=self.settings.deepseek_api_key,
                api_base="https://api.deepseek.com",
                temperature=0,
                max_tokens=2000,
                timeout=60,
                max_retries=0,
                http_async_client=http,
            ).bind(
                response_format={"type": "json_object"},
                extra_body={"thinking": {"type": "disabled"}},
            )
            with tracing_context(enabled=False):
                async with asyncio.timeout(60):
                    response = await model.ainvoke(
                        [
                            SystemMessage(content=system),
                            HumanMessage(content=payload),
                        ],
                        config={"callbacks": []},
                    )
            if not isinstance(response.content, str):
                raise ValueError("INVALID_OUTPUT")
            usage: dict[str, object] = dict(response.usage_metadata or {})
            if response.response_metadata.get("finish_reason") != "stop":
                raise ValueError("OUTPUT_TRUNCATED")
            return (
                response.content,
                int(str(usage.get("input_tokens", 0))),
                int(str(usage.get("output_tokens", 0))),
            )
