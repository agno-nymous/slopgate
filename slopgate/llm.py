import math
import os
import time
from typing import TYPE_CHECKING

from slopgate import trace
from slopgate.config import BASE_URL, MAX_OUTPUT_TOKENS, RATE_LIMIT_WAITS

if TYPE_CHECKING:
    from pydantic import BaseModel

usage: list[tuple[str, int, int]] = []


class CutOff(Exception):
    pass


def client():
    from openai import OpenAI

    return OpenAI(base_url=BASE_URL, api_key=os.environ["NEBIUS_API_KEY"])


def create(**request):
    from openai import RateLimitError

    for attempt, wait in enumerate(RATE_LIMIT_WAITS, 1):
        try:
            return client().chat.completions.create(**request)
        except RateLimitError as error:
            try:
                advised = float(error.response.headers["Retry-After"])
            except (KeyError, ValueError):
                advised = -1
            if advised >= 0:
                wait = min(advised, 60)
            with trace.span("llm.rate_limit", attempt=attempt, wait=wait):
                time.sleep(wait)
    return client().chat.completions.create(**request)


def complete(model: str, prompt: str) -> str:
    reply = create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=MAX_OUTPUT_TOKENS,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    usage.append((model, reply.usage.prompt_tokens, reply.usage.completion_tokens))
    if reply.choices[0].finish_reason == "length":
        raise CutOff("reply cut off")
    return reply.choices[0].message.content


def step(model: str, messages: list[dict], tools: list[dict]):
    reply = create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0,
        max_tokens=MAX_OUTPUT_TOKENS,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    usage.append((model, reply.usage.prompt_tokens, reply.usage.completion_tokens))
    if reply.choices[0].finish_reason == "length":
        raise CutOff("reply cut off")
    return reply.choices[0].message, reply.usage.prompt_tokens


def yes_probability(model: str, prompt: str) -> float:
    # The hook has a 30 s timeout, so it must not sleep on a 429.
    reply = client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1,
        logprobs=True,
        top_logprobs=5,
        # Without this, Lightning starts a reasoning preamble and the first token is "Here", not the answer.
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    usage.append((model, reply.usage.prompt_tokens, reply.usage.completion_tokens))
    top = {}
    # The sampled token can appear twice in top_logprobs; keep its first (largest) probability.
    for choice in reply.choices[0].logprobs.content[0].top_logprobs:
        top.setdefault(choice.token.strip().lower(), math.exp(choice.logprob))
    return top.get("yes", 0.0)


def decide[T: BaseModel](model: str, prompt: str, schema: type[T]) -> T | None:
    parameters = schema.model_json_schema()
    tool = {
        "type": "function",
        "function": {"name": schema.__name__, "description": parameters["description"], "parameters": parameters},
    }
    reply = create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        tools=[tool],
        tool_choice={"type": "function", "function": {"name": schema.__name__}},
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    usage.append((model, reply.usage.prompt_tokens, reply.usage.completion_tokens))
    calls = reply.choices[0].message.tool_calls
    if not calls:
        return None
    try:
        return schema.model_validate_json(calls[0].function.arguments)
    except ValueError:
        return None
