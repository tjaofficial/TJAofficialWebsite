from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Q
from ..models import Badge, ShowBadge, UserBadge, Show

def _now(): return timezone.now()

@login_required(login_url="/control/accounts/login/")
def tour_passport(request):
    user = request.user
    earned = (UserBadge.objects
              .filter(user=user)
              .select_related("badge","show")
              .order_by("-acquired_at"))

    total_points = sum(ub.badge.points for ub in earned)
    level = total_points // 50
    curr_floor = level * 50
    to_next = max(0, (level + 1) * 50 - total_points)
    level_progress = int(((total_points - curr_floor) / 50) * 100) if total_points >= curr_floor else 0
    show_badges_count = earned.filter(show__isnull=False).count()

    now = _now()
    upcoming = (ShowBadge.objects
        .select_related("show","badge")
        .filter(active=True)
        .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
        .order_by("show__date"))

    # next milestone
    milestones = (Badge.objects
        .filter(is_milestone=True, milestone_threshold__isnull=False)
        .order_by("milestone_threshold"))
    next_ms = None
    for m in milestones:
        if (m.milestone_threshold or 0) > show_badges_count:
            next_ms = m
            break
    ms_needed = (next_ms.milestone_threshold - show_badges_count) if next_ms else 0
    ms_progress = (show_badges_count / next_ms.milestone_threshold * 100) if next_ms else 100

    return render(request, "tour/passport.html", {
        "earned": earned,
        "total_points": total_points,
        "show_badges_count": show_badges_count,
        "upcoming": upcoming,
        "next_milestone": next_ms,
        "ms_needed": ms_needed,
        "ms_progress": int(ms_progress),
        "level": level,
        "to_next": to_next,
        "level_progress": level_progress,
    })

@login_required(login_url="/control/accounts/login/")
def tour_passport_redeem(request):
    code = (request.POST.get("code") or request.GET.get("code") or "").strip()
    if not code:
        messages.error(request, "Enter a code to redeem.")
        return redirect("tour_passport")

    # find matching ShowBadge (case-insensitive)
    try:
        sb = ShowBadge.objects.select_related("badge","show").get(code__iexact=code, active=True)
    except ShowBadge.DoesNotExist:
        messages.error(request, "Invalid or inactive code.")
        return redirect("tour_passport")

    # optional time window
    now = _now()
    if (sb.starts_at and now < sb.starts_at) or (sb.ends_at and now > sb.ends_at):
        messages.error(request, "That code isn't redeemable right now.")
        return redirect("tour_passport")

    # award if not already earned for this specific show+badge
    got, created = UserBadge.objects.get_or_create(
        user=request.user, badge=sb.badge, show=sb.show, defaults={"source":"code"}
    )
    if created:
        messages.success(request, f"Unlocked: {sb.badge.name} ✅")
    else:
        messages.info(request, "You already have this badge for that show.")

    # check milestone badges
    _maybe_award_milestones(request.user)

    return redirect("tour_passport")

def _maybe_award_milestones(user):
    # count show-based badges
    show_count = UserBadge.objects.filter(user=user, show__isnull=False).count()
    milestones = Badge.objects.filter(is_milestone=True, milestone_threshold__isnull=False)
    for m in milestones:
        if show_count >= (m.milestone_threshold or 1):
            UserBadge.objects.get_or_create(user=user, badge=m, show=None, defaults={"source":"milestone"})

def tour_passport_rules(request):
    return render(request, "tour/passport_rules.html")



#https://yourdomain.com/tour/passport/redeem/?code=DN25-DET-1
#QR code