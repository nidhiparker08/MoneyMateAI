import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import otp
from .forms import SignupForm
from .models import UserProfile

User = get_user_model()


def _stash_dev_code(request, result):
    """DEBUG-only convenience: remember the plain code so the OTP page can
    show it when Gmail filters the email. Never set in production."""
    if result.get("dev_code"):
        request.session["otp_dev_code"] = result["dev_code"]


def _wants_json(request) -> bool:
    """True for AJAX/fetch calls (same convention as settings_update)."""
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


def _pending_verification_user(request):
    """The user currently on the OTP screen (session-bound or logged-in-but-unverified)."""
    uid = request.session.get(otp.OTP_SESSION_KEY)
    if uid:
        user = User.objects.filter(id=uid).first()
        if user and not otp.is_email_verified(user):
            return user
    if request.user.is_authenticated and not otp.is_email_verified(request.user):
        return request.user
    return None


def _finish_verification(request, user):
    """Mark session clean and authenticate the user after a successful OTP."""
    request.session.pop(otp.OTP_SESSION_KEY, None)
    request.session.pop("otp_dev_code", None)
    if not request.user.is_authenticated:
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "Email verified — welcome to MoneyMate!")


def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            if User.objects.filter(email__iexact=email).exists():
                form.add_error(
                    "email",
                    "An account with this email already exists. Please sign in instead.",
                )
            else:
                user = form.save(commit=False)
                user.email = email
                user.set_password(form.cleaned_data["password"])
                user.save()

                # Pending (unverified) account — send the one-time OTP.
                record = otp.get_or_create_record(user)
                result = otp.issue_otp(user, record)
                _stash_dev_code(request, result)
                request.session[otp.OTP_SESSION_KEY] = user.id
                return redirect("accounts:verify_otp")
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            if not otp.is_email_verified(user):
                # Unverified account — complete signup with a one-time OTP.
                record = otp.get_or_create_record(user)
                result = otp.issue_otp(user, record)
                _stash_dev_code(request, result)
                request.session[otp.OTP_SESSION_KEY] = user.id
                if result["sent"]:
                    messages.info(request, result["message"])
                return redirect("accounts:verify_otp")
            login(request, user)
            return redirect("dashboard:index")
        messages.error(request, "Invalid username or password.")
    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("core:index")


# ==========================================================
# EMAIL OTP VERIFICATION
# ==========================================================

def verify_otp_view(request):
    """GET renders the OTP screen; POST verifies the code (JSON or form)."""
    user = _pending_verification_user(request)
    if user is None:
        if request.user.is_authenticated:
            return redirect("dashboard:index")
        return redirect("accounts:login")

    record = otp.get_or_create_record(user)

    error_message = ""
    info_message = ""

    if request.method == "POST":
        if _wants_json(request):
            try:
                body = json.loads(request.body.decode() or "{}")
            except (ValueError, UnicodeDecodeError):
                body = {}
            code = str(body.get("otp", ""))
        else:
            code = "".join(request.POST.getlist("otp"))

        status, message, extra = otp.verify_code(user, code)
        if status == "success":
            _finish_verification(request, user)
            if _wants_json(request):
                return JsonResponse({
                    "success": True,
                    "message": "Email verified — redirecting…",
                    "redirect": "/dashboard/",
                })
            return redirect("dashboard:index")

        if _wants_json(request):
            return JsonResponse({
                "success": False,
                "status": status,
                "message": message,
                "attempts_left": extra.get("attempts_left", 0),
                "resend_in": extra.get("resend_in", 0),
            }, status=400)
        error_message = message
    else:
        # Make sure a code exists on first page load (covers social signups
        # where the signal's send attempt failed — respects the cooldown).
        # Surface the outcome instead of failing silently.
        if not otp.code_is_active(record):
            result = otp.issue_otp(user, record)
            _stash_dev_code(request, result)
            if result["status"] == "error":
                error_message = result["message"]
            elif result["sent"]:
                info_message = result["message"]

    record.refresh_from_db()
    # DEBUG-only on-screen code (from the issuing call or the session).
    dev_code = request.session.get("otp_dev_code", "") if getattr(settings, "DEBUG", False) else ""
    return render(request, "accounts/verify_otp.html", {
        "masked_email": otp.mask_email(user.email),
        "error_message": error_message,
        "info_message": info_message,
        "resend_in": otp.cooldown_remaining(record),
        "dev_code": dev_code,
    })


@require_POST
def resend_otp_view(request):
    """Re-issue a fresh OTP (invalidates the old one, 60s cooldown)."""
    user = _pending_verification_user(request)
    if user is None:
        if _wants_json(request):
            return JsonResponse(
                {"success": False, "redirect": "/accounts/login/"}, status=401
            )
        return redirect("accounts:login")

    # Resend means "give me a new code" — invalidate the old one, but the
    # 60s cooldown still applies to prevent abuse.
    result = otp.issue_otp(user, force=True)
    _stash_dev_code(request, result)

    if _wants_json(request):
        status_code = 200
        if result["status"] == "cooldown":
            status_code = 429
        elif result["status"] == "error":
            status_code = 502
        return JsonResponse({
            "success": result["sent"],
            "status": result["status"],
            "message": result["message"],
            "resend_in": result["resend_in"],
            "dev_code": result.get("dev_code"),
        }, status=status_code)

    record = otp.get_or_create_record(user)
    return render(request, "accounts/verify_otp.html", {
        "masked_email": otp.mask_email(user.email),
        "error_message": "" if result["sent"] else result["message"],
        "info_message": result["message"] if result["sent"] else "",
        "resend_in": otp.cooldown_remaining(record),
        "dev_code": request.session.get("otp_dev_code", "")
        if getattr(settings, "DEBUG", False) else "",
    })


# ==========================================================
# PROFILE
# ==========================================================

def _get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@login_required
def profile_view(request):
    profile = _get_profile(request.user)

    # Stats to render on the profile card.
    tx_count = 0
    joined_days = 0
    from datetime import date
    try:
        from transactions.models import Transaction
        tx_count = Transaction.objects.filter(user=request.user).count()
    except Exception:
        pass
    if request.user.date_joined:
        joined_days = (date.today() - request.user.date_joined.date()).days

    # Connected accounts (Google via allauth if any)
    connected_accounts = []
    try:
        from allauth.socialaccount.models import SocialAccount
        for sa in SocialAccount.objects.filter(user=request.user):
            connected_accounts.append({
                "provider": sa.provider.capitalize(),
                "uid": sa.uid,
                "date_joined": sa.date_joined,
            })
    except Exception:
        pass

    # Connected banks
    connected_banks = []
    try:
        from transactions.bankhub_client import BankHubClient  # noqa: F401
        # If your BankHub client exposes a list, integrate here. Left generic on purpose.
    except Exception:
        pass

    return render(request, "accounts/profile.html", {
        "active_page": "profile",
        "profile": profile,
        "tx_count": tx_count,
        "joined_days": joined_days,
        "connected_accounts": connected_accounts,
        "connected_banks": connected_banks,
    })


@login_required
@require_POST
def profile_update(request):
    profile = _get_profile(request.user)
    user = request.user

    user.first_name = request.POST.get("first_name", user.first_name).strip()
    user.last_name = request.POST.get("last_name", user.last_name).strip()
    new_email = request.POST.get("email", user.email).strip()
    if new_email and new_email != user.email:
        user.email = new_email
    user.save()

    profile.display_name = request.POST.get("display_name", profile.display_name).strip()
    profile.phone = request.POST.get("phone", profile.phone).strip()
    profile.bio = request.POST.get("bio", profile.bio).strip()

    if request.FILES.get("avatar"):
        profile.avatar = request.FILES["avatar"]

    profile.save()
    return JsonResponse({
        "success": True,
        "message": "Profile updated.",
        "avatar_url": profile.avatar.url if profile.avatar else "",
    })


# ==========================================================
# SETTINGS
# ==========================================================

@login_required
def settings_view(request):
    profile = _get_profile(request.user)

    connected_accounts = []
    try:
        from allauth.socialaccount.models import SocialAccount
        for sa in SocialAccount.objects.filter(user=request.user):
            connected_accounts.append({
                "provider": sa.provider.capitalize(),
                "uid": sa.uid,
            })
    except Exception:
        pass

    # Import history (last 20)
    imports = []
    try:
        from transactions.models import Transaction
        imports = (
            Transaction.objects
            .filter(user=request.user)
            .exclude(import_source="manual")
            .values("import_source")
            .distinct()
        )
    except Exception:
        pass

    return render(request, "accounts/settings.html", {
        "active_page": "settings",
        "profile": profile,
        "connected_accounts": connected_accounts,
        "imports": list(imports),
        "theme_choices": UserProfile.THEME_CHOICES,
        "currency_choices": UserProfile.CURRENCY_CHOICES,
        "language_choices": UserProfile.LANGUAGE_CHOICES,
    })


@login_required
@require_POST
def settings_update(request):
    """Generic settings updater. Accepts any subset of the profile fields."""
    profile = _get_profile(request.user)

    field_map = {
        "theme": str,
        "currency": str,
        "timezone": str,
        "language": str,
        "notify_spending_alerts": lambda v: v in ("1", "true", "on"),
        "notify_budget_alerts": lambda v: v in ("1", "true", "on"),
        "notify_ai_insights": lambda v: v in ("1", "true", "on"),
        "notify_monthly_reports": lambda v: v in ("1", "true", "on"),
        "notify_bank_sync": lambda v: v in ("1", "true", "on"),
    }

    updated = []
    for field, caster in field_map.items():
        if field in request.POST:
            setattr(profile, field, caster(request.POST[field]))
            updated.append(field)
    profile.save()

    return JsonResponse({
        "success": True,
        "updated": updated,
        "theme": profile.theme,
    })


@login_required
def data_export(request):
    """Export all of the user's data as JSON."""
    from django.http import HttpResponse
    import json

    payload = {
        "user": {
            "username": request.user.username,
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "date_joined": request.user.date_joined.isoformat() if request.user.date_joined else None,
        },
        "transactions": [],
        "goals": [],
        "budgets": [],
        "holdings": [],
    }
    try:
        from transactions.models import Transaction
        for t in Transaction.objects.filter(user=request.user):
            payload["transactions"].append({
                "title": t.title,
                "merchant": t.merchant,
                "amount": float(t.amount),
                "type": t.transaction_type,
                "category": t.category.name if t.category else None,
                "date": t.transaction_date.isoformat(),
                "notes": t.notes,
            })
    except Exception:
        pass
    try:
        from goals.models import Goal
        for g in Goal.objects.filter(user=request.user):
            payload["goals"].append({
                "title": g.title,
                "target": float(g.target_amount),
                "current": float(g.current_amount),
                "deadline": g.deadline.isoformat(),
                "status": g.status,
            })
    except Exception:
        pass
    try:
        from budgets.models import Budget
        for b in Budget.objects.filter(user=request.user):
            payload["budgets"].append({
                "category": b.category.name if getattr(b, "category", None) else None,
                "amount": float(getattr(b, "amount", 0) or 0),
                "period": getattr(b, "period", ""),
            })
    except Exception:
        pass
    try:
        from investments.models import Holding
        for h in Holding.objects.filter(user=request.user):
            payload["holdings"].append({
                "symbol": h.symbol,
                "name": h.name,
                "quantity": float(h.quantity),
                "buy_price": float(h.buy_price),
                "current_price": float(h.current_price or 0),
                "asset_type": h.asset_type,
            })
    except Exception:
        pass

    body = json.dumps(payload, indent=2, default=str)
    resp = HttpResponse(body, content_type="application/json")
    resp["Content-Disposition"] = 'attachment; filename="finsync_export.json"'
    return resp
