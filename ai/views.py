import json
import os

from google import genai

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from .ai_services.chat_service import ChatService
from ai_memory.services import MemoryService

from .models import AIChatMessage
from .services import (
    compute_health_score,
    generate_insights,
)


@login_required
@ensure_csrf_cookie
def ai_page(request):
    from .insight_engine import generate_insights_v2, narrate_summary

    history = AIChatMessage.objects.filter(
        user=request.user, session_id="default"
    ).order_by("created_at")[:100]

    insights = generate_insights_v2(request.user, limit=6)
    narrative = narrate_summary(request.user, insights)

    context = {
        "active_page": "ai",
        "insights": insights,
        "narrative": narrative,
        "health": compute_health_score(request.user),
        "history": history,
    }
    return render(request, "ai/ai.html", context)


@login_required
@require_GET
def ai_health(request):
    return JsonResponse(compute_health_score(request.user))


@login_required
@require_GET
def ai_insights_api(request):
    from .insight_engine import generate_insights_v2, narrate_summary
    insights = generate_insights_v2(request.user, limit=6)
    return JsonResponse({
        "insights": insights,
        "narrative": narrate_summary(request.user, insights),
    })


@login_required
@require_POST
def ai_chat(request):
    """Non-streaming chat endpoint. Returns full assistant reply as JSON."""
    text = (request.POST.get("message") or "").strip()
    if not text:
        return JsonResponse({"success": False, "message": "Empty message"}, status=400)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return JsonResponse({
            "success": False,
            "message": "AI is not configured. Please contact support.",
        }, status=500)

    # Persist user message
    AIChatMessage.objects.create(user=request.user, role="user", content=text)

    try:
        chat_service = ChatService()

        reply = chat_service.generate_response(
            user=request.user,
            user_message=text,
        )

    except Exception as e:
        reply = f"Sorry, I hit an error reaching the AI: {str(e)}"

    AIChatMessage.objects.create(user=request.user, role="assistant", content=reply)

    try:
        memory_service = MemoryService()

        memory_service.process(
            user=request.user,
            message=text,
        )

    except Exception as e:
        print(f"AI Memory Error: {e}")

    return JsonResponse({"success": True, "reply": reply})


@login_required
@require_POST
def ai_clear(request):
    AIChatMessage.objects.filter(user=request.user, session_id="default").delete()
    return JsonResponse({"success": True})
