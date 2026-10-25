from types import SimpleNamespace

import httpx
import openai
import pytest

from slopgate import llm
from slopgate.review import SameJob


@pytest.fixture
def fake_client(monkeypatch):
    sent = []

    def respond(tool_calls):
        def create(**kwargs):
            sent.append(kwargs)
            message = SimpleNamespace(content=None, tool_calls=tool_calls)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3))

        monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
        monkeypatch.setattr(llm, "usage", [])
        return sent

    return respond


def tool_call(arguments):
    return [SimpleNamespace(function=SimpleNamespace(name="SameJob", arguments=arguments))]


def test_valid_tool_call_returns_the_object(fake_client):
    fake_client(tool_call('{"difference": "", "same_job": true}'))

    assert llm.decide("m", "p", SameJob) == SameJob(difference="", same_job=True)
    assert llm.usage == [("m", 7, 3)]


@pytest.mark.parametrize("tool_calls", [None, tool_call('{"same_job": true}')], ids=["no-tool-call", "missing-field"])
def test_unusable_reply_returns_none(fake_client, tool_calls):
    fake_client(tool_calls)

    assert llm.decide("m", "p", SameJob) is None


def test_request_forces_one_tool_with_every_field_description_and_thinking_off(fake_client):
    sent = fake_client(tool_call('{"difference": "", "same_job": false}'))

    llm.decide("m", "the prompt", SameJob)

    [request] = sent
    [tool] = request["tools"]
    assert tool["function"]["name"] == "SameJob"
    assert tool["function"]["description"] == SameJob.__doc__
    properties = tool["function"]["parameters"]["properties"]
    for name, field in SameJob.model_fields.items():
        assert properties[name]["description"] == field.description
    assert request["tool_choice"] == {"type": "function", "function": {"name": "SameJob"}}
    assert request["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert request["messages"] == [{"role": "user", "content": "the prompt"}]


def rate_limited(retry_after=None):
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    response = httpx.Response(429, headers=headers, request=httpx.Request("POST", "http://x"))
    return openai.RateLimitError("rate limited", response=response, body=None)


@pytest.fixture
def rate_limit(monkeypatch):
    sleeps = []
    monkeypatch.setattr(llm.time, "sleep", sleeps.append)

    def fail(errors):
        pending = list(errors)

        def create(**kwargs):
            if pending:
                raise pending.pop(0)
            message = SimpleNamespace(content=None, tool_calls=tool_call('{"difference": "", "same_job": true}'))
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3))

        monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
        monkeypatch.setattr(llm, "usage", [])
        return sleeps

    return fail


def test_rate_limit_is_retried_with_the_configured_waits(rate_limit):
    sleeps = rate_limit([rate_limited(), rate_limited()])

    assert llm.decide("m", "p", SameJob) == SameJob(difference="", same_job=True)
    assert sleeps == [5, 15]


def test_retry_after_header_wins_and_is_capped_at_60_seconds(rate_limit):
    sleeps = rate_limit([rate_limited("2"), rate_limited("999"), rate_limited("soon")])

    llm.decide("m", "p", SameJob)

    assert sleeps == [2, 60, 45]


@pytest.mark.parametrize("header", ["-1", "nan"])
def test_unusable_retry_after_falls_back_to_the_configured_wait(rate_limit, header):
    sleeps = rate_limit([rate_limited(header)])

    llm.decide("m", "p", SameJob)

    assert sleeps == [5]


def test_rate_limit_raises_after_the_waits_are_used_up(rate_limit):
    sleeps = rate_limit([rate_limited() for _ in range(4)])

    with pytest.raises(openai.RateLimitError):
        llm.decide("m", "p", SameJob)

    assert sleeps == [5, 15, 45]
