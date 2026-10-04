from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator

import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.utils import timezone

from .services import TransactionService
from .models import Transaction, TransactionCategory
from .forms import TransactionForm

from transactions.bankhub_client import BankHubClient
from investments.models import Holding


logger = logging.getLogger(__name__)


# ==========================================================
# Transactions Page
# ==========================================================

@login_required(login_url="accounts:login")
def transactions_page(request):

    # ==========================================
    # Filters
    # ==========================================

    search_query = request.GET.get("q", "").strip()

    selected_type = request.GET.get("type", "")

    selected_category = request.GET.get("category", "")

    sort = request.GET.get(
        "sort",
        "-transaction_date",
    )

    transactions = TransactionService.search_transactions(
        user=request.user,
        query=search_query,
        transaction_type=selected_type,
        category=selected_category,
        sort=sort,
    )

    transaction_count = transactions.count()

    paginator = Paginator(transactions, 15)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    transactions = page_obj.object_list

    # Real, data-driven insights (rule-based; fast per page render)
    try:
        from ai.insight_engine import generate_insights_v2
        _real_insights = generate_insights_v2(request.user, limit=4)
    except Exception:
        _real_insights = []

    total_income = sum(
        t.amount for t in transactions
        if t.transaction_type == "income"
    )

    total_expense = sum(
        t.amount for t in transactions
        if t.transaction_type == "expense"
    )

    context = {

        "page": "transactions",

        "transactions": page_obj,

        "categories":  TransactionCategory.objects.filter(
            user=request.user,
        ).order_by("name"),

        "transaction_form": TransactionForm(user=request.user),

        "total_income": total_income,

        "total_expense": total_expense,

        "net_savings": total_income - total_expense,

        "transaction_count": transaction_count,
        "page_obj": page_obj,

        "selected_type": selected_type,

        "selected_category": selected_category,

        "search_query": search_query,

        "selected_sort": sort,

        "selected_period": request.GET.get("period", "this_month"),

        "insights": _real_insights,

        "active_page": "transactions",

    }

    return render(
        request,
        "transactions/transactions.html",
        context,
    )


# ==========================================================
# Create Transaction
# ==========================================================

@login_required(login_url="accounts:login")
@require_POST
def create_transaction(request):

    form = TransactionForm(
        request.POST,
        user=request.user,
    )

    if not form.is_valid():

        return JsonResponse({

            "success": False,

            "errors": form.errors,

        }, status=400)

    transaction = TransactionService.create_transaction(

        user=request.user,

        title=form.cleaned_data["title"],

        merchant=form.cleaned_data["merchant"],

        amount=form.cleaned_data["amount"],

        transaction_type=form.cleaned_data["transaction_type"],

        category=form.cleaned_data["category"],

        payment_method=form.cleaned_data["payment_method"],

        transaction_date=form.cleaned_data["transaction_date"],

        transaction_time=form.cleaned_data["transaction_time"],

        notes=form.cleaned_data["notes"],

        goal=form.cleaned_data.get("goal"),

    )

    # If linked to a goal, update the goal's current amount.
    goal = form.cleaned_data.get("goal")
    if goal and transaction.transaction_type == "expense":
        from decimal import Decimal
        goal.current_amount = (goal.current_amount or Decimal("0")) + Decimal(str(transaction.amount))
        if goal.current_amount >= goal.target_amount:
            goal.current_amount = goal.target_amount
            goal.status = "completed"
        goal.save()

    return JsonResponse({

        "success": True,

        "message": "Transaction Added Successfully",

        "transaction": {

            "id": transaction.id,

            "title": transaction.title,

            "amount": float(transaction.amount),

            "type": transaction.transaction_type,

            "category": transaction.category.name if transaction.category else "",

        }

    })


# ==========================================================
# Delete Transaction
# ==========================================================

@login_required(login_url="accounts:login")
@require_POST
def delete_transaction(request, transaction_id):

    try:

        TransactionService.delete_transaction(

            request.user,

            transaction_id,

        )

        return JsonResponse({

            "success": True,

            "message": "Transaction deleted successfully."

        })

    except Exception as e:

        return JsonResponse({

            "success": False,

            "message": str(e)

        }, status=400)

# ==========================================================
# Get Transaction
# ==========================================================

@login_required(login_url="accounts:login")
@require_GET
def get_transaction(request, transaction_id):

    try:

        data = TransactionService.get_transaction_json(

            request.user,

            transaction_id,

        )

        return JsonResponse({

            "success": True,

            "transaction": data,

        })

    except Exception as e:

        return JsonResponse({

            "success": False,

            "message": str(e),

        }, status=404)

# ==========================================================
# Update Transaction
# ==========================================================

@login_required(login_url="accounts:login")
@require_POST
def update_transaction(request, transaction_id):

    form = TransactionForm(

        request.POST,

        user=request.user,

    )

    if not form.is_valid():

        return JsonResponse({

            "success": False,

            "errors": form.errors,

        }, status=400)

    transaction = TransactionService.update_transaction(

        request.user,

        transaction_id,

        title=form.cleaned_data["title"],

        merchant=form.cleaned_data["merchant"],

        amount=form.cleaned_data["amount"],

        transaction_type=form.cleaned_data["transaction_type"],

        category=form.cleaned_data["category"],

        payment_method=form.cleaned_data["payment_method"],

        transaction_date=form.cleaned_data["transaction_date"],

        transaction_time=form.cleaned_data["transaction_time"],

        notes=form.cleaned_data["notes"],

    )

    return JsonResponse({

        "success": True,

        "message": "Transaction updated successfully.",

        "transaction": {

            "id": transaction.id,

            "title": transaction.title,

            "amount": float(transaction.amount),

        }

    })

# ==========================================================
# BankHub Import
# ==========================================================

PAYMENT_METHOD_MAP = {
    "UPI": "upi",
    "Debit Card": "debit_card",
    "Credit Card": "credit_card",
    "NEFT": "net_banking",
    "RTGS": "net_banking",
    "IMPS": "net_banking",
    "ATM": "cash",
    "Cash": "cash",
    "Cheque": "cheque",
}

# Maps BankHub's investment "type" values to Holding.asset_type choices.
ASSET_TYPE_MAP = {
    "stock": "stock",
    "stocks": "stock",
    "equity": "stock",
    "mutual fund": "mutual_fund",
    "mutual_fund": "mutual_fund",
    "mf": "mutual_fund",
    "etf": "etf",
    "gold": "gold",
    "crypto": "crypto",
    "cryptocurrency": "crypto",
    "bond": "bond",
    "bonds": "bond",
    "fd": "fd",
    "fixed deposit": "fd",
    "fixed_deposit": "fd",
}


def _safe_str(value, default=""):
    """Return a stripped string, treating None/NaN as default."""
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_decimal(value, default="0"):
    """Coerce numeric-like values to Decimal. Falls back to default on failure."""
    if value is None or value == "":
        return Decimal(default)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _parse_date(value):
    """Parse a YYYY-MM-DD date string. Returns None on failure/empty."""
    text = _safe_str(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_time(value):
    """Parse a HH:MM:SS time string. Returns None on failure/empty."""
    text = _safe_str(value)
    if not text:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def _resolve_asset_type(raw_type):
    """Map BankHub's investment 'type' field to Holding.asset_type."""
    key = _safe_str(raw_type).lower()
    return ASSET_TYPE_MAP.get(key, "stock")


@login_required
@require_POST
def connect_bank(request):
    """
    BankHub → Transactions → Investments → AI Memory → Dashboard.

    Robust importer: any single malformed record is skipped, never
    aborts the whole import. Field access is defensive so that
    optional / renamed / null fields do not crash the flow.
    """

    # -----------------------------------------
    # Parse request body
    # -----------------------------------------
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid request payload."},
            status=400,
        )

    bank = _safe_str(data.get("bank"))
    name = _safe_str(data.get("name"))
    email = _safe_str(data.get("email"))
    phone = _safe_str(data.get("phone"))

    if not all([bank, name, email, phone]):
        return JsonResponse(
            {
                "success": False,
                "error": "Please fill in bank, name, email and phone.",
            },
            status=400,
        )

    # -----------------------------------------
    # Call BankHub API
    # -----------------------------------------
    try:
        bankhub = BankHubClient.connect_bank(
            bank=bank,
            name=name,
            email=email,
            phone=phone,
        )
    except Exception:
        logger.exception("BankHub connect_bank API call failed")
        return JsonResponse(
            {
                "success": False,
                "error": "Could not connect to bank right now. Please try again.",
            },
            status=502,
        )

    if not isinstance(bankhub, dict) or not bankhub.get("success", True):
        logger.error("BankHub returned unexpected payload: %r", bankhub)
        return JsonResponse(
            {
                "success": False,
                "error": "Bank returned an unexpected response. Please try again.",
            },
            status=502,
        )

    account = bankhub.get("account") or {}
    txn_list = bankhub.get("transactions") or []
    inv_list = bankhub.get("investments") or []

    imported_transactions = 0
    imported_investments = 0
    skipped_transactions = 0
    skipped_investments = 0

    created_transactions = []

    # -----------------------------------------
    # Transactions
    # -----------------------------------------

    for txn in txn_list:

        if not isinstance(txn, dict):
            skipped_transactions += 1
            continue

        try:

            txn_type = _safe_str(txn.get("type"), "expense").lower()
            if txn_type not in ("income", "expense"):
                txn_type = "expense"

            amount = _safe_decimal(txn.get("amount"))
            if amount <= 0:
                skipped_transactions += 1
                continue

            txn_date = _parse_date(txn.get("date"))
            if txn_date is None:
                skipped_transactions += 1
                continue

            txn_time = _parse_time(txn.get("time"))

            # Skip records that fall on upcoming days/hours — a
            # transaction cannot be dated in the future.
            _today = timezone.localdate()
            if txn_date > _today:
                skipped_transactions += 1
                continue
            if txn_date == _today and txn_time and txn_time > timezone.localtime().time():
                skipped_transactions += 1
                continue

            category_name = _safe_str(txn.get("category"), "Uncategorized")

            category, _ = TransactionCategory.objects.get_or_create(
                user=request.user,
                name=category_name,
                defaults={
                    "category_type": txn_type,
                    "is_default": False,
                },
            )

            title = _safe_str(
                txn.get("title"),
                _safe_str(txn.get("description"), "Transaction"),
            )

            transaction = Transaction.objects.create(
                user=request.user,
                category=category,
                title=title,
                merchant=_safe_str(txn.get("merchant")),
                transaction_type=txn_type,
                amount=amount,
                payment_method=PAYMENT_METHOD_MAP.get(
                    _safe_str(txn.get("payment_method")),
                    "other",
                ),
                import_source="bankhub",
                transaction_date=txn_date,
                transaction_time=txn_time,
                notes=_safe_str(txn.get("description")),
                receiver=_safe_str(txn.get("receiver")),
            )

            created_transactions.append(transaction)
            imported_transactions += 1

        except Exception:
            logger.exception(
                "BankHub: skipping malformed transaction record: %r", txn
            )
            skipped_transactions += 1
            continue

    # -----------------------------------------
    # Investments
    # -----------------------------------------

    for inv in inv_list:

        if not isinstance(inv, dict):
            skipped_investments += 1
            continue

        try:

            # BankHub schema:
            #   type, broker, name, symbol, quantity, buy_price,
            #   invested_amount, current_value, purchase_date
            symbol = _safe_str(inv.get("symbol"))
            inv_name = _safe_str(
                inv.get("name") or inv.get("instrument_name")
            )

            if not symbol and not inv_name:
                skipped_investments += 1
                continue

            quantity = _safe_decimal(inv.get("quantity"))
            buy_price = _safe_decimal(
                inv.get("buy_price") or inv.get("average_price")
            )

            # BankHub sends `current_value` as TOTAL market value.
            # Holding stores `current_price` per unit, so derive it.
            current_value = _safe_decimal(inv.get("current_value"))
            explicit_current_price = inv.get("current_price")

            if explicit_current_price is not None:
                current_price = _safe_decimal(explicit_current_price)
            elif quantity > 0 and current_value > 0:
                current_price = current_value / quantity
            else:
                current_price = buy_price

            asset_type = _resolve_asset_type(
                inv.get("type") or inv.get("investment_type")
            )

            Holding.objects.create(
                user=request.user,
                symbol=symbol or inv_name[:32],
                name=inv_name or symbol,
                asset_type=asset_type,
                quantity=quantity,
                buy_price=buy_price,
                current_price=current_price,
            )

            imported_investments += 1

        except Exception:
            logger.exception(
                "BankHub: skipping malformed investment record: %r", inv
            )
            skipped_investments += 1
            continue

    # -----------------------------------------
    # AI Memory learns from imported transactions
    # -----------------------------------------

    try:
        from financial_memory.services import memory_service
        memory_service.remember_correction(
            request.user,
            created_transactions,
        )
    except Exception:
        # Learning failure must not fail the whole import — the
        # dashboard/transactions/investments have already been persisted.
        logger.exception("BankHub: AI Memory learning step failed")

    # -----------------------------------------
    # Response (Dashboard reads the DB, so it refreshes automatically)
    # -----------------------------------------

    return JsonResponse({
        "success": True,
        "transactions_imported": imported_transactions,
        "investments_imported": imported_investments,
        "transactions_skipped": skipped_transactions,
        "investments_skipped": skipped_investments,
        "bank": _safe_str(account.get("bank"), bank),
    })
