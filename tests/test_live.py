import os

import pytest
from openai import OpenAI

from slopgate import config

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.environ.get("NEBIUS_API_KEY"), reason="NEBIUS_API_KEY not set"),
]


def test_config_model_ids_exist_in_token_factory():
    available = {m.id for m in OpenAI(base_url=config.BASE_URL, api_key=os.environ["NEBIUS_API_KEY"]).models.list()}
    nemotron = sorted(i for i in available if "nemotron" in i.lower())
    for model in (config.LIGHTNING, config.SUPER, config.ULTRA):
        assert model in available, f"{model} not in Token Factory; nemotron models: {nemotron}"
