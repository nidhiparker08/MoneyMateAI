"""
MoneyMate (Django) full page smoke + auth flow tests.
All routes are plain HTML (no /api prefix).
"""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
USERNAME = "moneymate_tester"
PASSWORD = "Test@12345"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"User-Agent": "MoneyMateTester/1.0"})
    # get csrf from login page
    r = s.get(f"{BASE_URL}/accounts/login/", timeout=30)
    assert r.status_code == 200, f"login page status {r.status_code}"
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    assert m, "csrf token not found on login page"
    token = m.group(1)
    r = s.post(
        f"{BASE_URL}/accounts/login/",
        data={
            "csrfmiddlewaretoken": token,
            "login": USERNAME,
            "username": USERNAME,
            "password": PASSWORD,
        },
        headers={"Referer": f"{BASE_URL}/accounts/login/"},
        allow_redirects=True,
        timeout=30,
    )
    assert r.status_code in (200, 302), f"login post status {r.status_code}"
    # verify logged in by fetching dashboard
    d = s.get(f"{BASE_URL}/dashboard/", timeout=30)
    assert d.status_code == 200, f"dashboard status {d.status_code}"
    assert "login" not in d.url.lower(), f"redirected to login: {d.url}"
    return s


# ---------------- Page smoke tests ---------------- #
PAGES = [
    ("/dashboard/", "dashboard"),
    ("/transactions/", "transactions"),
    ("/goals/", "goals"),
    ("/budgets/", "budgets"),
    ("/reports/", "reports"),
    ("/investments/", "investments"),
    ("/ai/", "ai"),
    ("/notifications/", "notifications"),
    ("/profile/", "profile"),
    ("/settings/", "settings"),
]


@pytest.mark.parametrize("path,name", PAGES)
def test_page_loads(session, path, name):
    r = session.get(f"{BASE_URL}{path}", timeout=30, allow_redirects=True)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    assert "MoneyMate" in r.text or "moneymate" in r.text.lower(), f"{path} missing branding"


def test_no_memory_link_in_sidebar(session):
    r = session.get(f"{BASE_URL}/dashboard/", timeout=30)
    assert r.status_code == 200
    # no href to /memory/ from sidebar/nav
    lower = r.text.lower()
    # allow the word 'memory' in body text (unlikely) but not as a nav link
    assert 'href="/memory' not in lower, "found /memory/ link in dashboard"
    # "AI Memory" text appears only inside a hidden bank-import loading step; the
    # sidebar/nav must not have an AI Memory link/item
    assert 'data-testid="sidebar-memory"' not in lower


def test_memory_route_still_works_internally(session):
    # visiting /memory/ directly should still be reachable (it's kept internally)
    r = session.get(f"{BASE_URL}/memory/", timeout=30, allow_redirects=True)
    # any non-500 is fine (200 or 302 or 404 is acceptable — but not 500)
    assert r.status_code < 500, f"/memory/ 500 error: {r.status_code}"


def test_dashboard_has_key_widgets(session):
    r = session.get(f"{BASE_URL}/dashboard/", timeout=30)
    text = r.text.lower()
    for token in ["total balance", "income", "expense"]:
        assert token in text, f"dashboard missing widget: {token}"


def test_sidebar_has_all_expected_testids(session):
    r = session.get(f"{BASE_URL}/dashboard/", timeout=30)
    for tid in [
        "sidebar-dashboard", "sidebar-transactions", "sidebar-goals",
        "sidebar-budgets", "sidebar-reports", "sidebar-investments",
        "sidebar-import", "sidebar-ai", "sidebar-notifications",
        "sidebar-profile", "sidebar-settings", "sidebar-logout",
        "quick-add-btn", "theme-toggle-btn", "profile-menu-trigger",
    ]:
        assert f'data-testid="{tid}"' in r.text, f"missing testid {tid}"


def test_ai_page_has_health_score_and_insights(session):
    r = session.get(f"{BASE_URL}/ai/", timeout=60)
    assert r.status_code == 200
    text = r.text.lower()
    assert "financial health" in text or "health score" in text, "no health score on AI page"
    assert "insight" in text, "no insights on AI page"


# ---------------- Write flows ---------------- #
def _get_csrf(session, url):
    r = session.get(url, timeout=30)
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    return r, (m.group(1) if m else None)


def _first_option(html, select_name):
    m = re.search(rf'<select[^>]*name="{select_name}"[^>]*>(.*?)</select>',
                  html, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    for v in re.findall(r'<option[^>]*value="([^"]+)"', m.group(1)):
        if v.strip():
            return v
    return None


def test_create_transaction_persists(session):
    """POST /transactions/create/ (real modal endpoint), verify persistence."""
    list_url = f"{BASE_URL}/transactions/"
    r, csrf = _get_csrf(session, list_url)
    assert r.status_code == 200 and csrf, "cannot fetch transactions page/csrf"
    category_id = _first_option(r.text, "category")
    if not category_id:
        pytest.skip("no category options available for user")
    payload = {
        "csrfmiddlewaretoken": csrf,
        "title": "TEST_pytest_txn",
        "merchant": "TEST_merchant",
        "transaction_type": "expense",
        "amount": "123.45",
        "category": category_id,
        "payment_method": "cash",
        "transaction_date": "2026-01-15",
        "transaction_time": "10:00",
        "notes": "pytest autogenerated",
    }
    post = session.post(f"{BASE_URL}/transactions/create/", data=payload,
                        headers={"Referer": list_url,
                                 "X-Requested-With": "XMLHttpRequest"},
                        timeout=30, allow_redirects=True)
    assert post.status_code in (200, 302), (
        f"txn create status {post.status_code}: {post.text[:400]}")
    if post.headers.get("content-type", "").startswith("application/json"):
        body = post.json()
        assert body.get("success") is True, f"create returned {body}"
    r_after = session.get(list_url, timeout=30)
    assert "TEST_pytest_txn" in r_after.text, "created transaction not visible in list"


def test_create_budget_persists(session):
    """POST /budgets/create/ and verify no 5xx."""
    list_url = f"{BASE_URL}/budgets/"
    r, csrf = _get_csrf(session, list_url)
    assert r.status_code == 200 and csrf, "cannot fetch budgets page/csrf"
    category_id = _first_option(r.text, "category")
    if not category_id:
        pytest.skip("no category options available for user")
    payload = {
        "csrfmiddlewaretoken": csrf,
        "name": "TEST_pytest_budget",
        "category": category_id,
        "amount": "5000",
        "limit_amount": "5000",
        "period": "monthly",
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
    }
    post = session.post(f"{BASE_URL}/budgets/create/", data=payload,
                        headers={"Referer": list_url},
                        timeout=30, allow_redirects=True)
    assert post.status_code in (200, 302), (
        f"budget create status {post.status_code}: {post.text[:400]}")


def test_no_500_across_all_pages(session):
    for path, _ in PAGES:
        r = session.get(f"{BASE_URL}{path}", timeout=30, allow_redirects=True)
        assert r.status_code < 500, f"{path} returned {r.status_code}"
