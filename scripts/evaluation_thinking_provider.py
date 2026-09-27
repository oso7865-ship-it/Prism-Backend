"""Synthetic evaluation only. Never wired into the product provider factory."""

import asyncio

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langsmith import tracing_context

from app.domain.review.harness import compose
from app.domain.review.policy import ReviewOutput
from app.domain.review.provider import DeepSeekProvider


class EvaluationThinkingProvider(DeepSeekProvider):
    async def review(self, payload: str) -> tuple[str, int, int]:
        if not self.settings.ai_enabled or not self.settings.deepseek_api_key:
            raise ValueError("AI_DISABLED")
        system, _ = compose(payload, ReviewOutput.model_json_schema())
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=90) as http:
            model = ChatDeepSeek(
                model_name=self.model,
                api_key=self.settings.deepseek_api_key,
                api_base="https://api.deepseek.com",
                max_tokens=4096,
                timeout=90,
                max_retries=0,
                http_async_client=http,
            ).bind(
                response_format={"type": "json_object"},
                extra_body={"thinking": {"type": "enabled"}, "reasoning_effort": "low"},
            )
            with tracing_context(enabled=False):
                async with asyncio.timeout(90):
                    response = await model.ainvoke(
                        [SystemMessage(content=system), HumanMessage(content=payload)],
                        config={"callbacks": []},
                    )
            if not isinstance(response.content, str):
                raise ValueError("INVALID_OUTPUT")
            if response.response_metadata.get("finish_reason") != "stop":
                raise ValueError("OUTPUT_TRUNCATED")
            usage: dict[str, object] = dict(response.usage_metadata or {})
            # Do not access, return or persist reasoning_content/additional_kwargs.
            return (
                response.content,
                int(str(usage.get("input_tokens", 0))),
                int(str(usage.get("output_tokens", 0))),
            )
