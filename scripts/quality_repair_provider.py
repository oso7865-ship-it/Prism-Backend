"""Evaluation-only transport/reasoning candidates; never changes production defaults."""

import asyncio
import json

import httpx

from app.domain.review.empty_review import EmptyReviewOutput
from app.domain.review.harness import compose, compose_empty_review, compose_verification
from app.domain.review.policy import ReviewOutput
from app.domain.review.provider import DeepSeekProvider
from app.domain.review.refinement import needs_reasoning
from app.domain.review.verification import VerificationOutput


class ResponsesCandidate(DeepSeekProvider):
    async def structured(self, system, payload, schema, *, transport=None):
        if not self.settings.ai_enabled or not self.settings.deepseek_api_key:
            raise ValueError("AI_DISABLED")
        async with (
            httpx.AsyncClient(
                trust_env=False,
                follow_redirects=False,
                timeout=60,
                transport=transport,
            ) as http,
            asyncio.timeout(60),
        ):
            async with http.stream(
                "POST",
                "https://api.deepseek.com/responses",
                headers={
                    "Authorization": "Bearer " + self.settings.deepseek_api_key.get_secret_value()
                },
                json={
                    "model": self.model,
                    "instructions": system,
                    "input": payload,
                    "reasoning": {"effort": self.reasoning_effort or "none"},
                    "temperature": 0,
                    "max_output_tokens": self.max_output_tokens,
                    "text": {"format": {"type": "json_schema", "name": "review", "schema": schema}},
                    "stream": False,
                },
            ) as response:
                response.raise_for_status()
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 256 * 1024:
                        raise ValueError("PROVIDER_RESPONSE_TOO_LARGE")
        data = json.loads(raw)
        if data.get("status") != "completed":
            raise ValueError("OUTPUT_TRUNCATED")
        # Only user-facing text is retained. Never log/persist a reasoning item.
        text = "".join(
            part["text"]
            for item in data.get("output", [])
            if item.get("type") == "message" and item.get("role") == "assistant"
            for part in item.get("content", [])
            if part.get("type") == "output_text"
        )
        if not text or len(text.encode()) > 24000:
            raise ValueError("INVALID_OUTPUT")
        usage = data.get("usage", {})
        return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0)

    async def review(self, payload):
        schema = ReviewOutput.model_json_schema()
        return await self.structured(compose(payload, schema)[0], payload, schema)

    async def verify(self, payload):
        return await self.structured(
            compose_verification(payload), payload, VerificationOutput.model_json_schema()
        )

    async def recheck_empty(self, payload):
        schema = EmptyReviewOutput.model_json_schema()
        return await self.structured(compose_empty_review(payload, schema), payload, schema)


class ConditionalCandidate(DeepSeekProvider):
    budget = 4000

    def second(self, payload):
        provider = DeepSeekProvider(self.settings)
        provider.max_output_tokens = self.budget
        provider.reasoning_effort = "high" if needs_reasoning(payload) else None
        return provider

    async def verify(self, payload):
        return await self.second(payload).verify(payload)

    async def recheck_empty(self, payload):
        return await self.second(payload).recheck_empty(payload)
