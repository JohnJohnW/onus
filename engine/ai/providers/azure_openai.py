"""Azure OpenAI provider, backed by the async OpenAI SDK's Azure client."""
from __future__ import annotations

import os

from ai.base import AIProvider

DEFAULT_API_VERSION = "2024-10-21"


class AzureOpenAIProvider(AIProvider):
    """AIProvider backed by Azure OpenAI.

    Configuration (environment):
        AZURE_OPENAI_ENDPOINT                 - required.
        AZURE_OPENAI_API_KEY                  - required.
        AZURE_OPENAI_DEPLOYMENT_NAME          - required (chat/completions deployment).
        AZURE_OPENAI_API_VERSION              - optional, defaults to ``2024-10-21``.
        AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME- required only for embed().

    Requires the ``openai`` package (``pip install openai``).
    """

    def __init__(self) -> None:
        try:
            from openai import AsyncAzureOpenAI
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for AzureOpenAIProvider. "
                "Install it with: pip install openai"
            ) from exc

        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")

        missing = [
            name
            for name, value in (
                ("AZURE_OPENAI_ENDPOINT", endpoint),
                ("AZURE_OPENAI_API_KEY", api_key),
                ("AZURE_OPENAI_DEPLOYMENT_NAME", self.deployment),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "Missing required Azure OpenAI environment variable(s): "
                + ", ".join(missing)
            )

        self.api_version = (
            os.environ.get("AZURE_OPENAI_API_VERSION") or DEFAULT_API_VERSION
        )
        # Azure serves embeddings from a separate deployment; only needed for embed().
        self.embedding_deployment = os.environ.get(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME"
        )
        self._client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=self.api_version,
        )

    async def complete(self, prompt: str, system: str = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        # On Azure, the ``model`` argument is the deployment name.
        resp = await self._client.chat.completions.create(
            model=self.deployment, messages=messages
        )
        return resp.choices[0].message.content or ""

    async def embed(self, text: str) -> list[float]:
        if not self.embedding_deployment:
            raise ValueError(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME is not set "
                "(required for embeddings with the Azure OpenAI provider)."
            )
        resp = await self._client.embeddings.create(
            model=self.embedding_deployment, input=text
        )
        return resp.data[0].embedding
