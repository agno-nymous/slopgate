import math
import os

from slopgate.config import BASE_URL

usage: list[tuple[str, int, int]] = []


def client():
    from openai import OpenAI

    return OpenAI(base_url=BASE_URL, api_key=os.environ["NEBIUS_API_KEY"])


def complete(model: str, prompt: str, json: bool = False) -> str:
    reply = client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        **({"response_format": {"type": "json_object"}} if json else {}),
    )
    usage.append((model, reply.usage.prompt_tokens, reply.usage.completion_tokens))
    return reply.choices[0].message.content


def yes_probability(model: str, prompt: str) -> float:
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
