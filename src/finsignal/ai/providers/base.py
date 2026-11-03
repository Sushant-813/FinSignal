"""Abstract provider interfaces and data contracts for AI model interaction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from finsignal.ai.context import InvestigationEvidenceContext


@dataclass(frozen=True)
class ProviderRequest:
    """Input payload contract passed to an AI model provider."""

    system_prompt: str
    user_prompt: str
    model: str
    timeout_seconds: float
    context: InvestigationEvidenceContext


@dataclass(frozen=True)
class ProviderResponse:
    """Raw model output and operational execution metadata."""

    raw_content: str
    provider: str
    model: str


class BaseLLMProvider(ABC):
    """Abstract contract for model provider implementations."""

    @abstractmethod
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Execute text generation request against target provider."""
        raise NotImplementedError
