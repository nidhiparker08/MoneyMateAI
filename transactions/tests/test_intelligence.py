"""
Unit tests for the Transaction Intelligence Layer.

Run with:
    python manage.py test transactions.tests.test_intelligence -v 2
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from transactions.intelligence import (
    DETAILED_TYPES,
    TransactionIntelligence,
    enrich_for_create,
)
from transactions.models import Transaction, TransactionCategory
from transactions.services import TransactionService


class TransactionIntelligenceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="intel_user", password="pw12345!"
        )
        # `create_default_categories` signal handles the categories.

    # ------------------------------------------------------------------
    # Pipeline priority: Financial Memory wins.
    # ------------------------------------------------------------------

    def test_memory_beats_dictionary(self):
        cat = TransactionCategory.objects.filter(user=self.user, name="Food").first()

        # Seed a few historical Swiggy tx that the user classified as
        # "Groceries" (deliberately non-default) to prove memory wins.
        groceries = TransactionCategory.objects.filter(user=self.user, name="Groceries").first()
        for _ in range(3):
            Transaction.objects.create(
                user=self.user,
                title="Swiggy Instamart",
                merchant="swiggy",
                amount=Decimal("500"),
                transaction_type="expense",
                category=groceries,
                subcategory="Instamart",
                transaction_type_detail="expense",
                payment_method="upi",
                transaction_date=date.today(),
                intelligence_source="manual",
            )

        result = TransactionIntelligence.analyze(
            "UPI/SWIGGY/PAYMENT/REF12345", user=self.user, direction="debit"
        )
        self.assertEqual(result["intelligence_source"], "memory")
        self.assertEqual(result["category"], "Groceries")
        self.assertGreaterEqual(result["confidence_score"], 70)

    # ------------------------------------------------------------------
    # 17 detailed types — each should classify from the description alone.
    # ------------------------------------------------------------------

    def test_salary_detected(self):
        r = TransactionIntelligence.analyze("NEFT SALARY CREDIT ACME PVT LTD", direction="credit")
        self.assertEqual(r["transaction_type_detail"], "salary")
        self.assertEqual(r["transaction_type"], "income")

    def test_dividend_detected(self):
        r = TransactionIntelligence.analyze("DIVIDEND PAYOUT RELIANCE 2024", direction="credit")
        self.assertEqual(r["transaction_type_detail"], "dividend")

    def test_interest_detected(self):
        r = TransactionIntelligence.analyze("INTEREST CREDIT FD 12345", direction="credit")
        self.assertEqual(r["transaction_type_detail"], "interest")

    def test_cashback_detected(self):
        r = TransactionIntelligence.analyze("CASHBACK PAYTM WALLET", direction="credit")
        self.assertEqual(r["transaction_type_detail"], "cashback")

    def test_refund_detected(self):
        r = TransactionIntelligence.analyze("REFUND FROM AMAZON REVERSAL", direction="credit")
        self.assertEqual(r["transaction_type_detail"], "refund")

    def test_investment_detected(self):
        r = TransactionIntelligence.analyze("SIP HDFC MUTUAL FUND", direction="debit")
        self.assertEqual(r["transaction_type_detail"], "investment")

    def test_insurance_detected(self):
        r = TransactionIntelligence.analyze("LIC INSURANCE PREMIUM PAID", direction="debit")
        self.assertEqual(r["transaction_type_detail"], "insurance")

    def test_loan_emi_detected(self):
        r = TransactionIntelligence.analyze("EMI HDFC HOME LOAN", direction="debit")
        self.assertEqual(r["transaction_type_detail"], "loan_emi")

    def test_subscription_detected(self):
        r = TransactionIntelligence.analyze("NETFLIX SUBSCRIPTION", direction="debit")
        self.assertEqual(r["transaction_type_detail"], "subscription")

    def test_utility_detected(self):
        r = TransactionIntelligence.analyze("BESCOM ELECTRICITY BILL", direction="debit")
        self.assertEqual(r["transaction_type_detail"], "utility_bill")

    def test_tax_detected(self):
        r = TransactionIntelligence.analyze("INCOME TAX ADVANCE PAYMENT", direction="debit")
        self.assertEqual(r["transaction_type_detail"], "tax")

    def test_internal_transfer_detected(self):
        r = TransactionIntelligence.analyze("SELF TRANSFER TO OWN A/C", direction="debit")
        self.assertEqual(r["transaction_type_detail"], "internal_transfer")

    def test_business_transfer_detected(self):
        r = TransactionIntelligence.analyze(
            "IMPS/P2A TO ACME PVT LTD 12345", direction="debit"
        )
        self.assertEqual(r["transaction_type_detail"], "business_transfer")

    def test_friend_transfer_detected(self):
        r = TransactionIntelligence.analyze(
            "UPI-987654-TO ANITA SHARMA-OKHDFCBANK", direction="debit"
        )
        self.assertEqual(r["transaction_type_detail"], "friend_transfer")
        self.assertTrue(r["receiver"].startswith("Anita"))

    def test_goal_contribution_detected(self):
        from goals.models import Goal
        from datetime import date, timedelta
        g = Goal.objects.create(
            user=self.user, title="Trip", goal_type="travel",
            target_amount=10000, current_amount=0,
            deadline=date.today() + timedelta(days=90),
            priority="medium", status="active", monthly_target=500,
        )
        r = TransactionIntelligence.analyze(
            "Monthly saving", direction="debit", user=self.user, goal=g
        )
        self.assertEqual(r["transaction_type_detail"], "goal_contribution")
        self.assertEqual(r["transaction_type"], "expense")

    def test_generic_income(self):
        r = TransactionIntelligence.analyze("Freelance from client", direction="credit")
        self.assertEqual(r["transaction_type"], "income")

    def test_generic_expense(self):
        r = TransactionIntelligence.analyze("Random cafe purchase", direction="debit")
        self.assertEqual(r["transaction_type"], "expense")

    # ------------------------------------------------------------------
    # All 17 declared types should be reachable from the pipeline.
    # ------------------------------------------------------------------

    def test_all_17_types_are_reachable(self):
        expected = {
            "income", "expense",
            "investment", "goal_contribution", "salary", "insurance",
            "loan_emi", "subscription", "utility_bill", "cashback",
            "refund", "interest", "dividend", "tax",
            "internal_transfer", "friend_transfer", "business_transfer",
        }
        self.assertEqual(expected, DETAILED_TYPES)

    # ------------------------------------------------------------------
    # Enrichment output shape
    # ------------------------------------------------------------------

    def test_output_contract(self):
        r = TransactionIntelligence.analyze("UPI/ZOMATO/PAYMENT", direction="debit")
        required = {
            "merchant", "receiver", "transaction_type",
            "transaction_type_detail", "category", "subcategory",
            "payment_method", "confidence_score", "intelligence_source",
            "trace",
        }
        self.assertTrue(required.issubset(r.keys()))
        self.assertIsInstance(r["confidence_score"], int)
        self.assertGreater(r["confidence_score"], 0)

    # ------------------------------------------------------------------
    # End-to-end via TransactionService — persistence works & no override
    # ------------------------------------------------------------------

    def test_service_persists_enrichment(self):
        food = TransactionCategory.objects.filter(user=self.user, name="Food").first()
        tx = TransactionService.create_transaction(
            user=self.user,
            title="Zomato order",
            amount=Decimal("450"),
            transaction_type="expense",
            category=food,
            payment_method="upi",
            transaction_date=date.today(),
        )
        self.assertEqual(tx.transaction_type, "expense")
        self.assertTrue(tx.transaction_type_detail)
        self.assertTrue(tx.merchant)
        self.assertGreater(tx.confidence_score, 0)
        # Existing explicit fields must NOT be overridden.
        self.assertEqual(tx.category, food)
        self.assertEqual(tx.payment_method, "upi")
