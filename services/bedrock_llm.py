"""
Bedrock Mantle LLM Service — OpenAI-compatible.

Uses the OpenAI SDK pointed at a Bedrock Mantle endpoint.
This gives us:
- Native async (no thread pool needed)
- Standard OpenAI message format
- Built-in streaming support
- Same SDK you'd use for GPT, just different base_url

Compatible with any OpenAI-style API:
- AWS Bedrock Mantle
- vLLM
- LiteLLM
- Ollama
- Any OpenAI-compatible proxy
"""

from dataclasses import dataclass
import time
import json
from typing import Optional, AsyncGenerator

from openai import AsyncOpenAI

from utils.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# RESPONSE DATA CLASS
# ─────────────────────────────────────────────
@dataclass
class LLMResponse:
    """
    Structured response from the LLM.

    Either content (text) or tool_calls will be populated,
    depending on what the LLM decides to do.
    """
    content: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    finish_reason: str = "stop"
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def has_tool_calls(self) -> bool:
        """Check if the response contains tool calls."""
        return bool(self.tool_calls)

    @property
    def has_content(self) -> bool:
        """Check if the response contains text content."""
        return bool(self.content)

@dataclass
class ToolCall:
    """A single tool call from the LLM."""
    id: str
    name: str
    arguments: dict

    @classmethod
    def from_openai(cls, tool_call) -> "ToolCall":
        """Create from OpenAI SDK tool call object."""
        return cls(
            id=tool_call.id,
            name=tool_call.function.name,
            arguments=json.loads(tool_call.function.arguments),
        )




class BedrockLLMService:
    """
    LLM service using Bedrock Mantle (OpenAI-compatible API).

    Usage:
        llm = BedrockLLMService(base_url="...", api_key="...", model_id="...")

        # Without tools
        response = await llm.generate(messages)

        # With tools
        response = await llm.generate(messages, tools=tool_definitions)
        if response.has_tool_calls:
            for tc in response.tool_calls:
                result = await execute_tool(tc.name, tc.arguments)
    """
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        max_tokens: int = 150,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: float = 30.0,
    ):
        """
        Initialize Bedrock Mantle LLM service.

        Args:
            base_url: Mantle endpoint URL (e.g., "https://mantle.example.com/v1")
            api_key: API key for the Mantle endpoint
            model_id: Bedrock model ID to use
            max_tokens: Maximum tokens in response
            temperature: Response temperature (0.0 - 1.0)
            top_p: Top-p sampling parameter
            timeout: Request timeout in seconds
        """
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p

        # Create OpenAI client pointed at Bedrock Mantle
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            default_headers={
                "Content-Type": "application/json",
            },
        )

        logger.info(
            "llm_initialized",
            base_url=base_url,
            model_id=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    # ─────────────────────────────────────────────
    # NON-STREAMING GENERATION
    # ─────────────────────────────────────────────

    async def generate(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        tool_choice: str = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) ->str:
        """
        Generate a response, optionally with tool calling.

        Args:
            messages: Conversation in OpenAI format
            tools: Tool definitions in OpenAI function calling format
            tool_choice: "auto" | "none" | {"type": "function", "function": {"name": "..."}}
            max_tokens: Override default
            temperature: Override default

        Returns:
            LLMResponse with content and/or tool_calls
        """
        start=time.time()
        max_tokens=max_tokens or self.max_tokens
        temperature=temperature or self.temperature

        logger.debug(
            "llm_generate_start",
            model_id=self.model_id,
            num_messages=len(messages),
            max_tokens=max_tokens,
            has_tools=bool(tools),
            num_tools=len(tools) if tools else 0,
        )

        try:
            # Build request kwargs
            kwargs = {
                "model": self.model_id,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": self.top_p,
            }
            # Add tools if provided
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice

            response = await self._client.chat.completions.create(**kwargs)
            # Parse response
            choice = response.choices[0]
            message = choice.message

            # Extract content
            content = message.content

            # Extract tool calls
            tool_calls = None
            if message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in message.tool_calls
                ]


            latency_ms = (time.time() - start) * 1000

            #Extract ussage metrics
            usage=response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            logger.info(
                "llm_generate_complete",
                latency_ms=round(latency_ms, 1),
                finish_reason=choice.finish_reason,
                has_content=bool(content),
                has_tool_calls=bool(tool_calls),
                num_tool_calls=len(tool_calls) if tool_calls else 0,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            if tool_calls:
                for tc in tool_calls:
                    logger.info(
                        "llm_tool_call",
                        tool_name=tc["name"],
                        tool_id=tc["id"],
                        arguments=tc["arguments"],
                    )
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            logger.error(
                "llm_generate_error",
                error=str(e),
                error_type=type(e).__name__,
                latency_ms=round(latency_ms, 1),
            )
            raise

    # ─────────────────────────────────────────────
    # STREAMING GENERATION
    # ─────────────────────────────────────────────

    async def generate_stream(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ):
        """Streaming generation — yields text chunks."""
        start = time.time()
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        kwargs = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": self.top_p,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = await self._client.chat.completions.create(**kwargs)

            total_text = ""
            first_token_latency = None

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    total_text += text

                    if first_token_latency is None:
                        first_token_latency = (time.time() - start) * 1000
                        logger.info("llm_first_token", first_token_latency_ms=round(first_token_latency, 1))

                    yield text

            total_latency_ms = (time.time() - start) * 1000
            logger.info(
                "llm_stream_complete",
                total_latency_ms=round(total_latency_ms, 1),
                response_length=len(total_text),
            )

        except Exception as e:
            logger.error("llm_stream_error", error=str(e))
            raise

    # ─────────────────────────────────────────────
    # HEALTH CHECK
    # ─────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Quick health check."""
        try:
            response = await self._client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0.0,
            )
            return bool(response.choices[0].message.content)
        except Exception as e:
            logger.error("llm_health_check_failed", error=str(e))
            return False