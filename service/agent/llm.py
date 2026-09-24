"""LLM client integration supporting OpenAI, Anthropic, Gemini, and local APIs with cost estimation."""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, NamedTuple

from service.agent.tools import TOOL_DEFINITIONS
from service.config import config

logger = logging.getLogger("autonomous_service.llm")

# Pricing per million tokens (input, output) in USD
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-2024-08-06": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "o1-mini": (3.00, 12.00),
    "o1-preview": (15.00, 60.00),
    # Anthropic
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-sonnet-latest": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (1.00, 5.00),
    "claude-3-opus-20240229": (15.00, 75.00),
    # Google Gemini
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-2.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
}


class ModelResponse(NamedTuple):
    text: str | None
    tool_calls: list[dict[str, Any]]
    input_tokens: int
    output_tokens: int


class LLMClient:
    def __init__(self, provider: str = "auto", model: str = "", api_key: str = "", api_base: str = ""):
        self.provider, self.model, self.api_key = self._resolve(provider, model, api_key)
        self.api_base = api_base
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def _resolve(self, provider: str, model: str, key: str) -> tuple[str, str, str]:
        if provider and provider != "auto" and key:
            return provider, model, key
        return config.resolve_provider_and_key()

    def get_estimated_cost_usd(self) -> float:
        """Estimate total dollar cost based on accumulated token usage."""
        input_rate, output_rate = (2.50, 10.00)  # default fallback pricing
        for model_key, (inp, outp) in MODEL_PRICING.items():
            if model_key in self.model.lower():
                input_rate, output_rate = inp, outp
                break
        cost = (self.total_input_tokens / 1_000_000.0) * input_rate + \
               (self.total_output_tokens / 1_000_000.0) * output_rate
        return round(cost, 6)

    def generate(self, messages: list[dict[str, Any]], system_prompt: str) -> ModelResponse:
        """Sends messages and tools to the active LLM provider."""
        if self.provider == "anthropic":
            resp = self._call_anthropic(messages, system_prompt)
        elif self.provider == "gemini":
            resp = self._call_gemini(messages, system_prompt)
        elif self.provider == "openai" or self.provider != "none":
            resp = self._call_openai_compatible(messages, system_prompt)
        else:
            raise RuntimeError("No valid LLM provider or API key configured.")

        self.total_input_tokens += resp.input_tokens
        self.total_output_tokens += resp.output_tokens
        return resp

    def _call_openai_compatible(self, messages: list[dict[str, Any]], system_prompt: str) -> ModelResponse:
        url = (self.api_base.rstrip("/") if self.api_base else "https://api.openai.com") + "/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        openai_messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": self.model or "gpt-4o",
            "messages": openai_messages,
            "tools": TOOL_DEFINITIONS,
            "tool_choice": "auto",
            "temperature": 0.1
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"OpenAI API error ({e.code}): {err_body}")
            raise RuntimeError(f"OpenAI API Error ({e.code}): {err_body}")

        choice = body["choices"][0]["message"]
        text = choice.get("content")
        tool_calls = []

        if choice.get("tool_calls"):
            for tc in choice["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                except Exception:
                    args = {}
                tool_calls.append({
                    "id": tc.get("id", f"call_{len(tool_calls)}"),
                    "name": tc["function"]["name"],
                    "input": args
                })

        usage = body.get("usage", {})
        inp_tokens = usage.get("prompt_tokens", 0)
        out_tokens = usage.get("completion_tokens", 0)

        return ModelResponse(text=text, tool_calls=tool_calls, input_tokens=inp_tokens, output_tokens=out_tokens)

    def _call_anthropic(self, messages: list[dict[str, Any]], system_prompt: str) -> ModelResponse:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        # Convert tool format to Anthropic
        anthropic_tools = []
        for t in TOOL_DEFINITIONS:
            fn = t["function"]
            anthropic_tools.append({
                "name": fn["name"],
                "description": fn["description"],
                "input_schema": fn["parameters"]
            })

        # Convert OpenAI-style message history to Anthropic format
        anthropic_messages = []
        for m in messages:
            role = m["role"]
            if role == "user":
                anthropic_messages.append({"role": "user", "content": m["content"]})
            elif role == "assistant":
                content = []
                if m.get("content"):
                    content.append({"type": "text", "text": m["content"]})
                if m.get("tool_calls"):
                    for tc in m["tool_calls"]:
                        content.append({
                            "type": "tool_use",
                            "id": tc.get("id", "call_1"),
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                        })
                anthropic_messages.append({"role": "assistant", "content": content})
            elif role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.get("tool_call_id", "call_1"),
                        "content": m.get("content", "")
                    }]
                })

        payload = {
            "model": self.model or "claude-3-5-sonnet-20241022",
            "system": system_prompt,
            "messages": anthropic_messages,
            "tools": anthropic_tools,
            "max_tokens": 4096,
            "temperature": 0.1
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"Anthropic API error ({e.code}): {err_body}")
            raise RuntimeError(f"Anthropic API Error ({e.code}): {err_body}")

        text_parts = []
        tool_calls = []
        for block in body.get("content", []):
            if block["type"] == "text":
                text_parts.append(block["text"])
            elif block["type"] == "tool_use":
                tool_calls.append({
                    "id": block["id"],
                    "name": block["name"],
                    "input": block["input"]
                })

        usage = body.get("usage", {})
        inp_tokens = usage.get("input_tokens", 0)
        out_tokens = usage.get("output_tokens", 0)

        return ModelResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            input_tokens=inp_tokens,
            output_tokens=out_tokens
        )

    def _call_gemini(self, messages: list[dict[str, Any]], system_prompt: str) -> ModelResponse:
        # Fallback to OpenAI-compatible interface for Gemini (via Google AI OpenAI endpoint)
        # https://generativelanguage.googleapis.com/v1beta/openai/
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        openai_messages = [{"role": "system", "content": system_prompt}] + messages
        payload = {
            "model": self.model or "gemini-2.5-flash",
            "messages": openai_messages,
            "tools": TOOL_DEFINITIONS,
            "tool_choice": "auto",
            "temperature": 0.1
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"Gemini API error ({e.code}): {err_body}")
            raise RuntimeError(f"Gemini API Error ({e.code}): {err_body}")

        choice = body["choices"][0]["message"]
        text = choice.get("content")
        tool_calls = []

        if choice.get("tool_calls"):
            for tc in choice["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                except Exception:
                    args = {}
                tool_calls.append({
                    "id": tc.get("id", f"call_{len(tool_calls)}"),
                    "name": tc["function"]["name"],
                    "input": args
                })

        usage = body.get("usage", {})
        inp_tokens = usage.get("prompt_tokens", 0)
        out_tokens = usage.get("completion_tokens", 0)

        return ModelResponse(text=text, tool_calls=tool_calls, input_tokens=inp_tokens, output_tokens=out_tokens)
