from types import SimpleNamespace

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
