from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Notification
from .services import unread_count


@login_required
def notifications_page(request):
    """Full notifications history page."""
    notifs = Notification.objects.filter(user=request.user).order_by("-created_at")[:300]

    context = {
        "active_page": "notifications",
        "notifications": notifs,
        "unread_count": unread_count(request.user),
        "total_count": Notification.objects.filter(user=request.user).count(),
    }
    return render(request, "notifications/notifications.html", context)


@login_required
@require_GET
def api_list(request):
    """Return the latest notifications + unread count for the bell dropdown."""
    limit = int(request.GET.get("limit", "12") or "12")
    limit = max(1, min(limit, 50))

    notifs = Notification.objects.filter(user=request.user).order_by("-created_at")[:limit]

    return JsonResponse({
        "success": True,
        "unread_count": unread_count(request.user),
        "notifications": [n.to_dict() for n in notifs],
    })


@login_required
@require_GET
def api_unread_count(request):
    return JsonResponse({"success": True, "unread_count": unread_count(request.user)})


@login_required
@require_POST
def api_mark_read(request):
    """Mark a single notification as read."""
    nid = request.POST.get("id")
    if not nid:
        return JsonResponse({"success": False, "message": "Missing id"}, status=400)

    n = get_object_or_404(Notification, pk=nid, user=request.user)
    if not n.is_read:
        n.is_read = True
        n.read_at = timezone.now()
        n.save(update_fields=["is_read", "read_at"])

    return JsonResponse({"success": True, "unread_count": unread_count(request.user)})


@login_required
@require_POST
def api_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    return JsonResponse({"success": True, "unread_count": 0})


@login_required
@require_POST
def api_dismiss(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.delete()
    return JsonResponse({"success": True, "unread_count": unread_count(request.user)})


@login_required
@require_POST
def api_clear_all(request):
    Notification.objects.filter(user=request.user).delete()
    return JsonResponse({"success": True, "unread_count": 0})


@login_required
@require_POST
def api_categorise_transaction(request, pk):
    """
    Handle the "categorise" action from an uncategorised-transaction
    notification. Sets the category on the transaction, teaches AI Memory,
    and resolves the notification in one atomic step.
    """
    from transactions.models import Transaction, TransactionCategory

    notif = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user,
        notif_type="uncategorised_transaction",
    )

    category_id = request.POST.get("category_id")
    remember = request.POST.get("remember", "true").lower() != "false"
    if not category_id:
        return JsonResponse({"success": False, "message": "Missing category_id"}, status=400)

    try:
        tx = Transaction.objects.get(id=notif.ref_id, user=request.user)
    except Transaction.DoesNotExist:
        notif.is_resolved = True
        notif.is_read = True
        notif.save(update_fields=["is_resolved", "is_read"])
        return JsonResponse({"success": False, "message": "Transaction no longer exists"}, status=404)

    try:
        cat = TransactionCategory.objects.get(id=category_id)
    except TransactionCategory.DoesNotExist:
        return JsonResponse({"success": False, "message": "Invalid category"}, status=400)

    tx.category = cat
    tx.save(update_fields=["category"])

    # Teach financial memory so we never need to ask again.
    if remember:
        try:
            from financial_memory.services import memory_service
            memory_service.remember_category(
                user=request.user,
                signal=tx.merchant or tx.title,
                category=cat,
                source="notification",
            )
        except Exception:
            pass

    notif.is_resolved = True
    notif.is_read = True
    notif.read_at = timezone.now()
    notif.save(update_fields=["is_resolved", "is_read", "read_at"])

    return JsonResponse({
        "success": True,
        "unread_count": unread_count(request.user),
        "message": f"Marked as {cat.name}.",
    })
