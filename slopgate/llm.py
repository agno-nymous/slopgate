import os

from openai import OpenAI

from slopgate.config import BASE_URL


def complete(model: str, prompt: str, json: bool = False) -> str:
    client = OpenAI(base_url=BASE_URL, api_key=os.environ["NEBIUS_API_KEY"])
    reply = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        **({"response_format": {"type": "json_object"}} if json else {}),
    )
    return reply.choices[0].message.content
