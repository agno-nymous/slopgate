import pytest
from test_duplicates import EMPTY, OTHER_JOB
from test_review import fenced, models, review

from slopgate.config import SUPER

COMPUTE_TAX = '''\
def compute_tax(amount, rate):
    return round(amount * rate, 2)
'''

TAX_FOR = '''

def tax_for(amount, rate):
    """Tax owed on an amount."""
    return compute_tax(amount, rate)
'''

INVOICE_TOTAL = '''

def invoice_total(subtotal):
    return subtotal + tax_for(subtotal, 0.2)
'''

INVOICE_TESTS = '''\
from app.billing import invoice_total


def test_hundred():
    assert invoice_total(100) == 120.0


def test_zero():
    assert invoice_total(0) == 0
'''


def test_same_file_wrapper_is_inlined_into_its_caller(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": "", "app/billing.py": COMPUTE_TAX},
        {"app/billing.py": COMPUTE_TAX + TAX_FOR + INVOICE_TOTAL},
    )
    fake_llm.replies += [OTHER_JOB, fenced(INVOICE_TESTS)]

    result = review(capsys, repo)

    assert models(fake_llm) == [SUPER, SUPER]
    assert "Call the function as `invoice_total`" in fake_llm.calls[1][1]
    assert result["suggestions"] == [] and result["rejected"] == []
    assert result["followup"] == [
        {
            "function": "tax_for",
            "kinds": ["wrapper"],
            "reason": "`tax_for` only forwards to `compute_tax`; inlined into its single caller `invoice_total` in app/billing.py. "
            "2 characterization tests of the caller passed.",
            "files": {"app/billing.py": COMPUTE_TAX + INVOICE_TOTAL.replace("tax_for(", "compute_tax(")},
        }
    ]


def test_caller_tests_run_on_the_rewrite(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": "", "app/billing.py": COMPUTE_TAX},
        {"app/billing.py": COMPUTE_TAX + TAX_FOR + INVOICE_TOTAL},
    )
    fake_llm.replies += [OTHER_JOB, fenced(INVOICE_TESTS + "\n\ndef test_wrapper_exists():\n    import app.billing\n\n    assert app.billing.tax_for\n")]

    result = review(capsys, repo)

    assert result["followup"] == []
    [rejected] = result["rejected"]
    assert (rejected["function"], rejected["path"]) == ("tax_for", "app/billing.py")
    assert rejected["reason"].startswith("rewrite fails characterization tests")
    assert "test_wrapper_exists" in rejected["reason"]


VIEWS = '''\
{imports}


def invoice_total(subtotal):
    return subtotal + tax_for(subtotal, 0.2)
'''


@pytest.mark.parametrize(
    ("base", "api", "imports", "fixed"),
    [
        (
            {"app/api.py": COMPUTE_TAX},
            COMPUTE_TAX + TAX_FOR,
            "from app.api import tax_for",
            "from app.api import compute_tax",
        ),
        (
            {"app/tax.py": COMPUTE_TAX},
            "from app.tax import compute_tax\n\nRATE = 0.2\n" + TAX_FOR,
            "from app.api import RATE, tax_for",
            "from app.api import RATE\nfrom app.tax import compute_tax",
        ),
    ],
    ids=["helper-defined-in-wrapper-module", "helper-imported-by-wrapper-module"],
)
def test_cross_file_wrapper_edits_both_files(make_repo, fake_llm, capsys, base, api, imports, fixed):
    repo = make_repo({"app/__init__.py": "", **base}, {"app/api.py": api, "app/views.py": VIEWS.format(imports=imports)})
    fake_llm.replies += [OTHER_JOB, fenced(INVOICE_TESTS.replace("app.billing", "app.views"))]

    result = review(capsys, repo)

    assert models(fake_llm) == [SUPER, SUPER]
    assert result["rejected"] == []
    [followup] = result["followup"]
    assert followup["reason"].startswith("`tax_for` only forwards to `compute_tax`; inlined into its single caller `invoice_total` in app/views.py.")
    assert followup["files"] == {
        "app/api.py": api.removesuffix(TAX_FOR),
        "app/views.py": VIEWS.format(imports=fixed).replace("tax_for(", "compute_tax("),
    }


@pytest.mark.parametrize(
    ("wrapper", "call", "inlined", "want"),
    [
        (TAX_FOR, "tax_for(a * 2, r)", "compute_tax(a * 2, r)", 10.0),
        (TAX_FOR, "tax_for(rate=r, amount=a)", "compute_tax(a, r)", 5.0),
        (TAX_FOR.replace("rate):", "rate=0.5):"), "tax_for(a) * r", "compute_tax(a, 0.5) * r", 2.5),
    ],
    ids=["expressions", "keywords", "default"],
)
def test_call_site_arguments_fill_the_inner_call(make_repo, fake_llm, capsys, wrapper, call, inlined, want):
    caller = f"\n\ndef total(a, r):\n    return {call}\n"
    repo = make_repo({"app/__init__.py": "", "app/billing.py": COMPUTE_TAX}, {"app/billing.py": COMPUTE_TAX + wrapper + caller})
    fake_llm.replies += [OTHER_JOB, fenced(f"from app.billing import total\n\n\ndef test_total():\n    assert total(10, 0.5) == {want}\n")]

    [followup] = review(capsys, repo)["followup"]

    assert followup["files"] == {"app/billing.py": COMPUTE_TAX + caller.replace(call, inlined)}


RECEIPT_LINE = '''

def receipt_line(price):
    return f"tax {tax_for(price, 0.1)}"
'''

INVOICE_METHOD = '''

class Invoice:
    def total(self, subtotal):
        return subtotal + tax_for(subtotal, 0.2)
'''


@pytest.mark.parametrize(
    ("callers", "same_job_checks"), [(INVOICE_TOTAL + RECEIPT_LINE, 1), (INVOICE_METHOD, 0)], ids=["two-callers", "method-caller"]
)
def test_wrapper_without_one_function_caller_is_left_alone(make_repo, fake_llm, capsys, callers, same_job_checks):
    repo = make_repo(
        {"app/__init__.py": "", "app/billing.py": COMPUTE_TAX},
        {"app/billing.py": COMPUTE_TAX + TAX_FOR + callers},
    )
    fake_llm.replies += [OTHER_JOB] * same_job_checks

    assert review(capsys, repo) == EMPTY
    assert models(fake_llm) == [SUPER] * same_job_checks


@pytest.mark.parametrize(
    ("wrapper", "call"),
    [
        (TAX_FOR, "tax_for(rate=float(r), amount=abs(a))"),
        (TAX_FOR.replace("rate):", "rate=RATES[0]):"), "tax_for(a) * r"),
    ],
    ids=["reordered-calls", "non-constant-default"],
)
def test_inlining_that_would_change_evaluation_is_left_alone(make_repo, fake_llm, capsys, wrapper, call):
    caller = f"\n\nRATES = [0.5]\n\n\ndef total(a, r):\n    return {call}\n"
    repo = make_repo({"app/__init__.py": "", "app/billing.py": COMPUTE_TAX}, {"app/billing.py": COMPUTE_TAX + wrapper + caller})
    fake_llm.replies += [OTHER_JOB]

    assert review(capsys, repo) == EMPTY
    assert models(fake_llm) == [SUPER]


def test_tests_prompt_shows_the_code_the_target_calls(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": "", "app/tax.py": COMPUTE_TAX},
        {
            "app/billing.py": "from app.tax import compute_tax\n" + TAX_FOR + INVOICE_TOTAL,
        },
    )
    fake_llm.replies += [OTHER_JOB, fenced(INVOICE_TESTS)]

    review(capsys, repo)

    [_, (_, prompt)] = fake_llm.calls
    context = prompt.split("Code it calls")[1]
    assert "# app/billing.py\n" + TAX_FOR.strip() in context
    assert "# app/tax.py\n" + COMPUTE_TAX.strip() in context
    assert "def invoice_total" not in context


APPLY_DISCOUNT = '''\
def apply_discount(price, percent):
    if percent < 0 or percent > 100:
        raise ValueError("percent must be 0-100")
    return round(price * (100 - percent) / 100, 2)
'''


@pytest.mark.live
def test_real_super_proves_a_wrapper_whose_caller_depends_on_the_helper(make_repo, capsys):
    wrapper = '\n\ndef discounted(price, percent):\n    """Return the price after the discount."""\n    return apply_discount(price, percent)\n'
    cart = "from shop.pricing import discounted\n\n\ndef cart_total(prices, percent):\n    return sum(discounted(p, percent) for p in prices)\n"
    repo = make_repo(
        {"shop/__init__.py": "", "shop/pricing.py": APPLY_DISCOUNT},
        {"shop/pricing.py": APPLY_DISCOUNT + wrapper, "shop/cart.py": cart},
    )

    result = review(capsys, repo, "contree")

    assert result["rejected"] == []
    [followup] = result["followup"]
    assert followup["files"] == {"shop/pricing.py": APPLY_DISCOUNT, "shop/cart.py": cart.replace("discounted", "apply_discount")}
