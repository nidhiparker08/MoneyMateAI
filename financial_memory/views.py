"""HTTP views for the Financial Memory Engine.

These views back the ``/memory/`` section of the site: a small dashboard that
surfaces what the engine has learnt, and a review queue where the user can
classify uncertain transactions.
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from transactions.models import TransactionCategory
from goals.models import Goal

from .models import (
    ENTITY_TYPES,
    MemoryEntry,
    MerchantAlias,
    RECURRING_PATTERN_TYPES,
    RecurringPattern,
    ReviewQueueItem,
)
from .services import memory_service, RecurringDetector


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required(login_url="accounts:login")
def memory_dashboard(request):
    stats = memory_service.stats_for_user(request.user)

    recent_entries = (
        MemoryEntry.objects
        .filter(user=request.user)
        .select_related("linked_category", "linked_goal", "linked_holding")
        .order_by("-updated_at")[:20]
    )

    recurring_patterns = (
        RecurringPattern.objects
        .filter(user=request.user, is_active=True)
        .order_by("-confidence", "-occurrences_count")[:12]
    )

    pending_reviews = (
        ReviewQueueItem.objects
        .filter(user=request.user, status="pending")
        .order_by("-created_at")[:5]
    )

    aliases = (
        MerchantAlias.objects
        .filter(user=request.user, is_active=True)
        .order_by("canonical_name")[:20]
    )

    # ------------------------------------------------------------------
    # What Memory Knows (unique learned entities)
    # ------------------------------------------------------------------

    entity_counts = [
        (
            "Goal",
            MemoryEntry.objects.filter(
                user=request.user,
                is_active=True,
                linked_goal__isnull=False,
            ).values("linked_goal").distinct().count(),
        ),
        (
            "Category",
            MemoryEntry.objects.filter(
                user=request.user,
                is_active=True,
                linked_category__isnull=False,
            ).values("linked_category").distinct().count(),
        ),
        (
            "Investment",
            MemoryEntry.objects.filter(
                user=request.user,
                is_active=True,
                linked_holding__isnull=False,
            ).values("linked_holding").distinct().count(),
        ),
        (
            "Merchant Alias",
            MerchantAlias.objects.filter(
                user=request.user,
                is_active=True,
            ).count(),
        ),
    ]

    entity_counts = [item for item in entity_counts if item[1] > 0]

    entity_type_labels = {
        "Goal": "Goal",
        "Category": "Category",
        "Investment": "Investment",
        "Merchant Alias": "Merchant Alias",
    }

    context = {
        "active_page": "memory",
        "page": "memory",
        "stats": stats,
        "recent_entries": recent_entries,
        "recurring_patterns": recurring_patterns,
        "pending_reviews": pending_reviews,
        "aliases": aliases,
        "entity_counts": entity_counts,
        "entity_type_labels": entity_type_labels,
        "pattern_type_labels": dict(RECURRING_PATTERN_TYPES),
    }
    return render(request, "financial_memory/dashboard.html", context)


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------

@login_required(login_url="accounts:login")
def review_queue(request):
    status = request.GET.get("status", "pending")
    qs = ReviewQueueItem.objects.filter(user=request.user)
    if status in {"pending", "reviewed", "dismissed", "auto_resolved"}:
        qs = qs.filter(status=status)
    qs = qs.select_related("transaction").order_by("-created_at")

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    categories = (
        TransactionCategory.objects
        .filter(user=request.user)
        .order_by("category_type", "name")
    )
    goals = Goal.objects.filter(user=request.user, status="active").order_by("deadline")

    context = {
        "active_page": "memory",
        "page": "memory",
        "page_obj": page_obj,
        "items": page_obj.object_list,
        "status": status,
        "categories": categories,
        "goals": goals,
        "entity_types": ENTITY_TYPES,
        "pending_count": ReviewQueueItem.objects.filter(user=request.user, status="pending").count(),
    }
    return render(request, "financial_memory/review_queue.html", context)


@login_required(login_url="accounts:login")
@require_POST
def resolve_review(request, item_id):
    category_id = request.POST.get("category")
    goal_id = request.POST.get("goal")
    entity_type = (request.POST.get("entity_type") or "category").strip()
    entity_value = (request.POST.get("entity_value") or "").strip()

    category = None
    if category_id:
        category = TransactionCategory.objects.filter(id=category_id).first()
    goal = None
    if goal_id:
        goal = Goal.objects.filter(id=goal_id, user=request.user).first()

    try:
        entry = memory_service.resolve_review(
            user=request.user,
            review_id=item_id,
            category=category,
            goal=goal,
            entity_type=entity_type,
            entity_value=entity_value or (category.name if category else "") or (goal.title if goal else ""),
        )
    except ReviewQueueItem.DoesNotExist:
        return JsonResponse({"success": False, "message": "Review item not found."}, status=404)

    return JsonResponse({
        "success": True,
        "message": "Learned. Future similar transactions will be classified automatically.",
        "memory_id": entry.id if entry else None,
    })


@login_required(login_url="accounts:login")
@require_POST
def dismiss_review(request, item_id):
    ReviewQueueItem.objects.filter(id=item_id, user=request.user).update(status="dismissed")
    return JsonResponse({"success": True})


# ---------------------------------------------------------------------------
# Entry management
# ---------------------------------------------------------------------------

@login_required(login_url="accounts:login")
def entries_list(request):
    entity_type = request.GET.get("entity_type", "")
    q = (request.GET.get("q") or "").strip()

    entries = (
        MemoryEntry.objects
        .filter(user=request.user)
        .select_related("linked_category", "linked_goal", "linked_holding")
    )
    if entity_type:
        entries = entries.filter(entity_type=entity_type)
    if q:
        entries = entries.filter(signal_key__icontains=q)

    entries = entries.order_by("-updated_at")
    paginator = Paginator(entries, 30)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "active_page": "memory",
        "page": "memory",
        "page_obj": page_obj,
        "entries": page_obj.object_list,
        "entity_types": ENTITY_TYPES,
        "selected_entity_type": entity_type,
        "search_query": q,
    }
    return render(request, "financial_memory/entries_list.html", context)


@login_required(login_url="accounts:login")
@require_POST
def delete_entry(request, entry_id):
    MemoryEntry.objects.filter(id=entry_id, user=request.user).delete()
    return JsonResponse({"success": True, "message": "Memory entry deleted."})


@login_required(login_url="accounts:login")
@require_POST
def toggle_entry(request, entry_id):
    entry = get_object_or_404(MemoryEntry, id=entry_id, user=request.user)
    entry.is_active = not entry.is_active
    entry.save(update_fields=["is_active"])
    return JsonResponse({"success": True, "is_active": entry.is_active})


# ---------------------------------------------------------------------------
# Recurring detection trigger
# ---------------------------------------------------------------------------

@login_required(login_url="accounts:login")
@require_POST
def detect_recurring_view(request):
    patterns = RecurringDetector.detect_for_user(request.user)
    return JsonResponse({
        "success": True,
        "count": len(patterns),
        "message": f"Detected {len(patterns)} recurring pattern(s).",
    })


# ---------------------------------------------------------------------------
# JSON classification API (used by import previews & JS)
# ---------------------------------------------------------------------------

@login_required(login_url="accounts:login")
def api_classify(request):
    description = request.GET.get("description") or request.POST.get("description") or ""
    if not description:
        return JsonResponse({"success": False, "message": "description required"}, status=400)
    result = memory_service.classify(request.user, description)
    return JsonResponse({"success": True, "result": result.to_dict()})
