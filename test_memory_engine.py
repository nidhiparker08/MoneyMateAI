"""End-to-end validation of the Financial Memory Engine.

Runs as a plain Python script to keep it independent of pytest and Django's
`test` runner:

    cd /app/backend && python test_memory_engine.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FinSyncAI.settings")
django.setup()

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client

from transactions.models import Transaction, TransactionCategory
from transactions.services import TransactionService
from transactions.importers.categorizer import TransactionCategorizer
from goals.models import Goal
from financial_memory.models import (
    MemoryEntry,
    MerchantAlias,
    RecurringPattern,
    ReviewQueueItem,
)
from financial_memory.services import memory_service, RecurringDetector, normalise_signal

RESULTS = []


def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    RESULTS.append((tag, name, detail))
    print(f"[{tag}] {name}{(': ' + detail) if detail else ''}")


def cleanup(user):
    Transaction.objects.filter(user=user).delete()
    MemoryEntry.objects.filter(user=user).delete()
    MerchantAlias.objects.filter(user=user).delete()
    RecurringPattern.objects.filter(user=user).delete()
    ReviewQueueItem.objects.filter(user=user).delete()
    Goal.objects.filter(user=user).delete()


def get_or_create_user():
    user, created = User.objects.get_or_create(
        username="memtest",
        defaults={"email": "memtest@example.com"},
    )
    if created or not user.has_usable_password():
        user.set_password("memtestpass123")
        user.save()
    return user


def test_normalisation():
    print("\n[TEST] Signal normalisation")
    checks = {
        "UPI-12345-GROWW PAYMENT": "groww",
        "POS AMAZON PAY INDIA": "amazon pay",
        "IMPS To Rahul REF 999123456": "rahul",
        "SALARY CREDIT ABC PVT LTD": "salary credit abc",
    }
    for raw, expected_sub in checks.items():
        got = normalise_signal(raw)
        check(f"normalise({raw!r}) contains {expected_sub!r}", expected_sub in got, f"got={got!r}")


def test_learn_and_recall(user):
    print("\n[TEST] remember_correction learns categories, merchants and goals")

    cat_investment, _ = TransactionCategory.objects.get_or_create(
        user=user, name="Investment", defaults={"category_type": "expense"}
    )

    # 1. User manually creates a Groww transaction, assigns Investment cat.
    tx = TransactionService.create_transaction(
        user=user, title="Groww SIP", amount=Decimal("5000"),
        transaction_type="expense", category=cat_investment,
        payment_method="upi", transaction_date=date.today(),
        merchant="Groww",
    )

    entries = MemoryEntry.objects.filter(user=user, entity_type="category")
    check("Category memory created for Groww", entries.filter(signal_key="groww").exists())

    # 2. New unrelated bank statement row lands - "GROWW INVEST 45324" should
    #    be auto-classified via memory.
    result = memory_service.classify(user, "GROWW INVEST 45324")
    check(
        "classify auto-suggests Investment category for new Groww txn",
        result.confidence >= 60 and result.category.lower() == "investment",
        f"result={result.to_dict()}",
    )
    check(
        "classify returns memory as source (not static)",
        result.source == "memory",
        f"source={result.source}",
    )


def test_goal_memory(user):
    print("\n[TEST] Goal contributions produce goal memory")
    goal = Goal.objects.create(
        user=user,
        title="Bike Savings",
        target_amount=Decimal("50000"),
        deadline=date.today() + timedelta(days=365),
    )
    cat_transfer, _ = TransactionCategory.objects.get_or_create(
        user=user, name="Transfer", defaults={"category_type": "expense"}
    )
    tx = TransactionService.create_transaction(
        user=user, title="Bike Savings Transfer", amount=Decimal("2000"),
        transaction_type="expense", category=cat_transfer,
        payment_method="upi", transaction_date=date.today(),
        merchant="Bike Savings", goal=goal,
    )

    hit = memory_service.classify(user, "Bike Savings Transfer 1234")
    check("Goal memory recalled for Bike Savings", hit.linked_goal_id == goal.id, f"got={hit.linked_goal_id}")


def test_salary_memory(user):
    print("\n[TEST] Salary transactions register a salary_source")
    cat_salary, _ = TransactionCategory.objects.get_or_create(
        user=user, name="Salary", defaults={"category_type": "income"}
    )
    TransactionService.create_transaction(
        user=user, title="ABC Pvt Ltd Salary Credit", amount=Decimal("70000"),
        transaction_type="income", category=cat_salary,
        payment_method="net_banking", transaction_date=date.today(),
        merchant="ABC Pvt Ltd",
    )
    sal = MemoryEntry.objects.filter(user=user, entity_type="salary_source")
    check("Salary source memory persisted", sal.exists(), f"count={sal.count()}")


def test_categorizer_uses_memory(user):
    print("\n[TEST] Static categorizer consults memory when user is provided")
    # Build a memory that would never come from the static db.
    memory_service.remember(
        user=user,
        signal_type="merchant",
        signal_key="grocery abc",
        raw_signal="Grocery ABC",
        entity_type="category",
        entity_value="Groceries",
        confidence=95,
    )
    result_with = TransactionCategorizer.categorize("Grocery ABC purchase", user=user)
    result_without = TransactionCategorizer.categorize("Grocery ABC purchase")
    check(
        "categorizer(user=user) returns memory result",
        result_with.get("category") == "Groceries" and result_with.get("memory") is True,
        f"got={result_with}",
    )
    check(
        "categorizer(no user) does NOT return memory-based result",
        result_without.get("memory") is not True,
        f"got={result_without}",
    )


def test_review_queue(user):
    print("\n[TEST] Review queue enqueue/resolve cycle")
    item = memory_service.enqueue_review(
        user=user,
        original_description="MYSTERY MERCHANT 7788 UPI DEBIT",
        merchant_guess="MYSTERY MERCHANT",
        amount=Decimal("399"),
        transaction_type="expense",
        transaction_date=date.today(),
        source="csv",
        confidence=25,
    )
    check("Review item enqueued", item is not None and item.status == "pending")

    cat, _ = TransactionCategory.objects.get_or_create(
        user=user, name="Subscriptions", defaults={"category_type": "expense"}
    )
    memory_service.resolve_review(
        user=user, review_id=item.id, category=cat,
        entity_type="subscription", entity_value="Mystery Merchant",
    )
    item.refresh_from_db()
    check("Review resolved", item.status == "reviewed")

    # Now future transactions matching the same signal should be auto-classified.
    hit = memory_service.classify(user, "MYSTERY MERCHANT charge OCT 2025")
    check(
        "Resolved review teaches future classification",
        hit.confidence >= 60 and hit.category == "Subscriptions",
        f"got={hit.to_dict()}",
    )


def test_recurring_detection(user):
    print("\n[TEST] Recurring pattern detection")
    cat_sub, _ = TransactionCategory.objects.get_or_create(
        user=user, name="Entertainment", defaults={"category_type": "expense"}
    )
    for i in range(5):
        d = date.today() - timedelta(days=30 * i)
        TransactionService.create_transaction(
            user=user, title="Netflix Subscription", amount=Decimal("499"),
            transaction_type="expense", category=cat_sub,
            payment_method="upi", transaction_date=d,
            merchant="Netflix",
        )
    patterns = RecurringDetector.detect_for_user(user)
    netflix = next((p for p in patterns if "netflix" in p.merchant_key), None)
    check("Netflix detected as recurring", netflix is not None)
    if netflix:
        check(
            f"Frequency identified as monthly ({netflix.frequency})",
            netflix.frequency == "monthly",
            f"got={netflix.frequency}",
        )
        check(
            f"Occurrence count >= 5 ({netflix.occurrences_count})",
            netflix.occurrences_count >= 5,
        )


def test_http_views(user):
    print("\n[TEST] HTTP views respond correctly")
    c = Client()
    logged_in = c.login(username=user.username, password="memtestpass123")
    check("Login as test user", logged_in)

    resp = c.get("/memory/")
    check("GET /memory/ 200", resp.status_code == 200, f"status={resp.status_code}")

    resp = c.get("/memory/review/")
    check("GET /memory/review/ 200", resp.status_code == 200)

    resp = c.get("/memory/entries/")
    check("GET /memory/entries/ 200", resp.status_code == 200)

    resp = c.get("/memory/api/classify/?description=GROWW+INVEST+9999")
    check("GET /memory/api/classify/ 200", resp.status_code == 200)
    if resp.status_code == 200:
        data = resp.json()
        check("classify API returns memory result", data.get("success") and data["result"]["category"] == "Investment", f"data={data}")


def main():
    user = get_or_create_user()
    cleanup(user)

    test_normalisation()
    test_learn_and_recall(user)
    test_goal_memory(user)
    test_salary_memory(user)
    test_categorizer_uses_memory(user)
    test_review_queue(user)
    test_recurring_detection(user)
    test_http_views(user)

    failed = [r for r in RESULTS if r[0] == "FAIL"]
    print("\n" + "=" * 60)
    print(f"TOTAL: {len(RESULTS)}  PASS: {len(RESULTS) - len(failed)}  FAIL: {len(failed)}")
    if failed:
        print("\nFAILURES:")
        for _, name, detail in failed:
            print(f"  \u2718 {name} \u2014 {detail}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
