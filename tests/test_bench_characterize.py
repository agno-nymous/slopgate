from bench.characterize import mutants
from slopgate.functions import parse


def test_mutants_change_one_site_each_and_keep_the_rest_of_the_file():
    text = "import os\n\n\ndef f(a, b):\n    return a < 3 and b\n\n\nX = 1\n"
    [f] = parse("app/m.py", text)
    head, tail = "import os\n\n\n", "\n\nX = 1\n"
    control, texts = mutants(f, text)
    assert texts == [
        head + "def f(a, b):\n    return None\n" + tail,
        head + "def f(a, b):\n    return a < 3 or b\n" + tail,
        head + "def f(a, b):\n    return a >= 3 and b\n" + tail,
        head + "def f(a, b):\n    return a < 4 and b\n" + tail,
    ]
    assert control == text


def test_mutants_of_a_decorated_method_keep_the_decorator_and_the_indentation():
    text = "class C:\n    @property\n    def g(self):\n        if self.x:\n            return 1\n"
    [f] = parse("app/m.py", text)
    head = "class C:\n    @property\n    def g(self):\n"
    control, texts = mutants(f, text)
    assert texts == [
        head + "        if not self.x:\n            return 1\n",
        head + "        if self.x:\n            return None\n",
        head + "        if self.x:\n            return 2\n",
    ]
    assert control == text
