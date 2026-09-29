"""Evaluation profile for both review stages; no raw reasoning access or persistence."""

from app.domain.review.provider import DeepSeekProvider


class ReasoningQualityProvider(DeepSeekProvider):
    reasoning_effort = "high"
    max_output_tokens = 8192


class HybridQualityProvider(DeepSeekProvider):
    """Fast draft followed by a different DeepSeek model for independent checking."""

    def checker(self):
        provider = ReasoningQualityProvider(
            self.settings.model_copy(update={"deepseek_model": "deepseek-v4-pro"})
        )
        provider.reasoning_effort = "low"
        return provider

    async def verify(self, payload):
        return await self.checker().verify(payload)

    async def recheck_empty(self, payload):
        return await self.checker().recheck_empty(payload)
