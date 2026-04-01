from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib import messages
from django.urls import reverse
from .models import Subscriber, Tag, EmailCampaignRecipient, EmailCampaign, EmailTemplate
from .forms import CampaignComposeForm
from rewards.models import CustomerProfile
from events.models import Event
from tickets.models import Ticket
from .forms import SubscriberForm, BulkSendForm
from coreutils.mailer import enqueue_mass_email
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import EmailMultiAlternatives
from collections import OrderedDict
from django.utils import timezone
from django.conf import settings
import re
import uuid
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

is_super = user_passes_test(lambda u: u.is_superuser)

@is_super
def subscribers_list(request):
    q = request.GET.get("q", "").strip()
    qs = Subscriber.objects.all()
    if q:
        qs = qs.filter(
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(city__icontains=q) |
            Q(state__icontains=q)
        )
    return render(request, "subscribers/subscribers.html", {"subs": qs, "q": q})

@is_super
def subscriber_add(request):
    form = SubscriberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("control:subscribers:list")
    return render(request, "subscribers/add.html", {"form": form})

@is_super
def subscriber_detail(request, pk):
    s = get_object_or_404(Subscriber, pk=pk)
    return render(request, "subscribers/detail.html", {"s": s})


def split_name_parts(full_name: str):
    full_name = (full_name or "").strip()
    if not full_name:
        return "", ""
    parts = full_name.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])

def upsert_subscriber_from_email(email, first_name="", last_name="", source="ticket_purchase"):
    email = (email or "").strip().lower()
    if not email:
        return None

    subscriber, created = Subscriber.objects.get_or_create(
        email=email,
        defaults={
            "first_name": (first_name or "").strip(),
            "last_name": (last_name or "").strip(),
            "source": source,
            "consent": True,
            "is_subscribed": True,
            "unsubscribe_token": uuid.uuid4(),
        }
    )

    changed = False

    if first_name and not subscriber.first_name:
        subscriber.first_name = first_name.strip()
        changed = True

    if last_name and not subscriber.last_name:
        subscriber.last_name = last_name.strip()
        changed = True

    if not subscriber.source:
        subscriber.source = source
        changed = True

    if not subscriber.unsubscribe_token:
        subscriber.unsubscribe_token = uuid.uuid4()
        changed = True

    if changed:
        subscriber.save()

    return subscriber

def sync_ticket_buyers_to_subscribers(event=None):
    qs = Ticket.objects.exclude(purchaser_email__isnull=True).exclude(purchaser_email__exact="")
    if event:
        qs = qs.filter(ticket_type__event=event)

    for ticket in qs.iterator():
        first_name, last_name = split_name_parts(ticket.purchaser_name)
        upsert_subscriber_from_email(
            email=ticket.purchaser_email,
            first_name=first_name,
            last_name=last_name,
            source="ticket_purchase",
        )

def get_subscriber_audience():
    qs = Subscriber.objects.filter(
        consent=True,
        is_subscribed=True,
    ).order_by("email")

    return [
        {
            "email": s.email,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "full_name": s.full_name,
            "source": "subscriber",
            "subscriber": s,
            "ticket_count": None,
        }
        for s in qs
    ]

def get_ticket_buyer_audience(event):
    sync_ticket_buyers_to_subscribers(event=event)

    raw_tickets = (
        Ticket.objects
        .filter(ticket_type__event=event)
        .exclude(purchaser_email__isnull=True)
        .exclude(purchaser_email__exact="")
        .order_by("purchaser_email", "id")
    )

    deduped = OrderedDict()

    for ticket in raw_tickets:
        email = (ticket.purchaser_email or "").strip().lower()
        if not email:
            continue

        first_name, last_name = split_name_parts(ticket.purchaser_name)
        subscriber = upsert_subscriber_from_email(
            email=email,
            first_name=first_name,
            last_name=last_name,
            source="ticket_purchase",
        )

        if not subscriber or not subscriber.is_subscribed:
            continue

        if email not in deduped:
            deduped[email] = {
                "email": email,
                "first_name": subscriber.first_name,
                "last_name": subscriber.last_name,
                "full_name": subscriber.full_name,
                "source": "ticket_buyer",
                "subscriber": subscriber,
                "ticket_count": 1,
            }
        else:
            deduped[email]["ticket_count"] += 1

    return list(deduped.values())

def get_rewards_audience():
    """
    Adjust field names to match your real rewards model.
    Assumes:
      - email
      - first_name
      - last_name
      - is_active (optional)
    """
    qs = CustomerProfile.objects.exclude(user__email__isnull=True).exclude(user__email__exact="")

    # Optional filter if your model has something like is_active
    if hasattr(CustomerProfile, "is_active"):
        qs = qs.filter(user__is_active=True)

    deduped = OrderedDict()

    for acct in qs.order_by("user__email"):
        email = (acct.user.email or "").strip().lower()
        if not email:
            continue

        subscriber = upsert_subscriber_from_email(
            email=email,
            first_name=getattr(acct.user, "first_name", "") or "",
            last_name=getattr(acct.user, "last_name", "") or "",
            source="rewards_account",
        )

        if not subscriber or not subscriber.is_subscribed:
            continue

        if email not in deduped:
            deduped[email] = {
                "email": email,
                "first_name": subscriber.first_name,
                "last_name": subscriber.last_name,
                "full_name": subscriber.full_name,
                "source": "rewards_account",
                "subscriber": subscriber,
                "ticket_count": None,
            }

    return list(deduped.values())

def merge_audiences(*audience_lists):
    """
    Dedupes by email across multiple audience sources.
    """
    merged = OrderedDict()

    for audience in audience_lists:
        for row in audience:
            email = (row.get("email") or "").strip().lower()
            if not email:
                continue

            if email not in merged:
                merged[email] = row
            else:
                existing_source = merged[email].get("source", "")
                new_source = row.get("source", "")
                if new_source and new_source not in existing_source:
                    merged[email]["source"] = f"{existing_source}, {new_source}".strip(", ")

                if not merged[email].get("first_name") and row.get("first_name"):
                    merged[email]["first_name"] = row.get("first_name", "")
                if not merged[email].get("last_name") and row.get("last_name"):
                    merged[email]["last_name"] = row.get("last_name", "")
                if not merged[email].get("full_name") and row.get("full_name"):
                    merged[email]["full_name"] = row.get("full_name", "")
                if not merged[email].get("subscriber") and row.get("subscriber"):
                    merged[email]["subscriber"] = row.get("subscriber")

    return list(merged.values())

def ensure_subscriber_unsubscribe_token(subscriber):
    if subscriber and not subscriber.unsubscribe_token:
        subscriber.unsubscribe_token = uuid.uuid4()
        subscriber.save(update_fields=["unsubscribe_token"])
    return subscriber

def format_event_date(event):
    if not event or not getattr(event, "start", None):
        return ""
    return timezone.localtime(event.start).strftime("%A, %B %d, %Y at %-I:%M %p")

def render_campaign_content(raw_text, context):
    """
    Replaces merge tags like {{ first_name }} with context values.
    Keeps HTML intact if you include HTML in the body.
    """
    text = raw_text or ""

    replacements = {
        "first_name": context.get("first_name", "") or "",
        "last_name": context.get("last_name", "") or "",
        "full_name": context.get("full_name", "") or "",
        "email": context.get("email", "") or "",
        "event_name": context.get("event_name", "") or "",
        "event_date": context.get("event_date", "") or "",
    }

    for key, value in replacements.items():
        text = re.sub(r"{{\s*" + re.escape(key) + r"\s*}}", str(value), text)

    return text

def build_campaign_context(subscriber=None, event=None, email=""):
    first_name = ""
    last_name = ""
    full_name = ""

    if subscriber:
        first_name = subscriber.first_name or ""
        last_name = subscriber.last_name or ""
        full_name = subscriber.full_name or ""

    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "email": email or (subscriber.email if subscriber else ""),
        "event_name": str(event) if event else "",
        "event_date": format_event_date(event),
    }

def build_marketing_email_html(rendered_body, unsubscribe_url, recipient_name=""):
    greeting = f"<p style='margin-top:0;'>Hey {recipient_name},</p>" if recipient_name else "<p style='margin-top:0;'>Hey,</p>"

    return f"""
    <html>
      <body style="margin:0; padding:0; background:#0f1115; font-family:Arial, Helvetica, sans-serif; color:#111;">
        <div style="max-width:680px; margin:0 auto; padding:32px 20px;">
          <div style="background:#ffffff; border-radius:18px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,.25);">
            <div style="background:linear-gradient(135deg, #111827, #1f2937); padding:28px 24px; color:#fff;">
              <h1 style="margin:0; font-size:28px; line-height:1.2;">TJAofficial</h1>
              <p style="margin:8px 0 0; opacity:.85;">Updates, shows, drops, and more.</p>
            </div>

            <div style="padding:28px 24px; font-size:16px; line-height:1.7; color:#111;">
              {greeting}
              <div>{rendered_body}</div>
            </div>

            <div style="padding:20px 24px; background:#f4f5f7; font-size:13px; color:#555; border-top:1px solid #e5e7eb;">
              <p style="margin:0 0 10px;">
                You're receiving this because you subscribed for updates or purchased tickets.
              </p>
              <p style="margin:0;">
                <a href="{unsubscribe_url}" style="color:#2563eb; text-decoration:none;">Unsubscribe from future marketing emails</a>
              </p>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

@staff_member_required
def audience_outreach(request):
    events = Event.objects.filter(published=True).select_related("venue").order_by("-start")
    templates = EmailTemplate.objects.all().order_by("title")
    drafts = EmailCampaign.objects.filter(status="draft").order_by("-created_at")

    audience_type = request.GET.get("audience_type") or request.POST.get("audience_type") or "subscribers"
    event_id = request.GET.get("event_id") or request.POST.get("event_id")
    selected_event = None
    audience = []

    if audience_type == "ticket_buyers" and event_id:
        selected_event = get_object_or_404(Event, pk=event_id)
        audience = get_ticket_buyer_audience(selected_event)

    elif audience_type == "subscribers":
        audience = get_subscriber_audience()

    elif audience_type == "rewards_accounts":
        audience = get_rewards_audience()

    elif audience_type == "all_audiences":
        subscriber_audience = get_subscriber_audience()
        rewards_audience = get_rewards_audience()

        if event_id:
            selected_event = get_object_or_404(Event, pk=event_id)
            ticket_audience = get_ticket_buyer_audience(selected_event)
        else:
            ticket_audience = []

        audience = merge_audiences(subscriber_audience, rewards_audience, ticket_audience)

    preview_html = ""
    preview_subject = (request.POST.get("subject") or "").strip()
    preview_body = (request.POST.get("body") or "").strip()
    preview_mode = False

    draft_title_value = request.POST.get("title", "") if request.method == "POST" else ""
    draft_subject_value = request.POST.get("subject", "") if request.method == "POST" else ""
    draft_body_value = request.POST.get("body", "") if request.method == "POST" else ""
    draft_test_email_value = request.POST.get("test_email", "") if request.method == "POST" else ""
    selected_template_id = request.POST.get("template_id", "") if request.method == "POST" else ""
    selected_draft_id = request.POST.get("draft_id", "") if request.method == "POST" else ""

    if request.method == "POST":
        action = request.POST.get("action", "send")
        title = (request.POST.get("title") or "").strip()
        subject = (request.POST.get("subject") or "").strip()
        body = (request.POST.get("body") or "").strip()
        test_email = (request.POST.get("test_email") or "").strip()
        selected_emails = [e.strip().lower() for e in request.POST.getlist("selected_emails") if e.strip()]
        template_id = (request.POST.get("template_id") or "").strip()
        draft_id = (request.POST.get("draft_id") or "").strip()

        if audience_type == "ticket_buyers":
            if not event_id:
                messages.error(request, "Select an event first.")
                return redirect(reverse("control:subscribers:audience_outreach") + "?audience_type=ticket_buyers")
            selected_event = get_object_or_404(Event, pk=event_id)
            audience = get_ticket_buyer_audience(selected_event)

        elif audience_type == "subscribers":
            audience = get_subscriber_audience()

        elif audience_type == "rewards_accounts":
            audience = get_rewards_audience()

        elif audience_type == "all_audiences":
            subscriber_audience = get_subscriber_audience()
            rewards_audience = get_rewards_audience()

            if event_id:
                selected_event = get_object_or_404(Event, pk=event_id)
                ticket_audience = get_ticket_buyer_audience(selected_event)
            else:
                ticket_audience = []

            audience = merge_audiences(subscriber_audience, rewards_audience, ticket_audience)

        valid_lookup = {row["email"]: row for row in audience}
        chosen_rows = [valid_lookup[email] for email in selected_emails if email in valid_lookup]

        if action == "load_template":
            if not template_id:
                messages.error(request, "Choose a template to load.")
            else:
                template = get_object_or_404(EmailTemplate, pk=template_id)
                draft_title_value = template.title
                draft_subject_value = template.subject
                draft_body_value = template.body
                selected_template_id = str(template.id)
                messages.success(request, f'Template "{template.title}" loaded.')

        elif action == "save_template":
            if not title:
                messages.error(request, "Template title is required.")
            elif not subject:
                messages.error(request, "Template subject is required.")
            elif not body:
                messages.error(request, "Template body is required.")
            else:
                template, created = EmailTemplate.objects.update_or_create(
                    title=title,
                    defaults={
                        "subject": subject,
                        "body": body,
                        "created_by": request.user,
                    }
                )
                selected_template_id = str(template.id)
                messages.success(
                    request,
                    f'Template "{template.title}" {"created" if created else "updated"}.'
                )

        elif action == "load_draft":
            if not draft_id:
                messages.error(request, "Choose a draft to load.")
            else:
                draft_obj = get_object_or_404(EmailCampaign, pk=draft_id, status="draft")
                draft_title_value = draft_obj.title
                draft_subject_value = draft_obj.subject
                draft_body_value = draft_obj.body
                selected_draft_id = str(draft_obj.id)

                if draft_obj.audience_type:
                    audience_type = draft_obj.audience_type
                if draft_obj.event_id_snapshot:
                    event_id = str(draft_obj.event_id_snapshot)
                    if audience_type == "ticket_buyers":
                        selected_event = get_object_or_404(Event, pk=draft_obj.event_id_snapshot)
                        audience = get_ticket_buyer_audience(selected_event)
                messages.success(request, f'Draft "{draft_obj.title or draft_obj.subject}" loaded.')

        elif action == "save_draft":
            if not subject:
                messages.error(request, "Draft subject is required.")
            elif not body:
                messages.error(request, "Draft body is required.")
            else:
                if draft_id:
                    draft_obj = get_object_or_404(EmailCampaign, pk=draft_id, status="draft")
                    draft_obj.title = title
                    draft_obj.subject = subject
                    draft_obj.body = body
                    draft_obj.audience_type = audience_type
                    draft_obj.event_id_snapshot = selected_event.id if selected_event else None
                    draft_obj.event_name_snapshot = str(selected_event) if selected_event else ""
                    draft_obj.created_by = request.user
                    draft_obj.save()
                else:
                    draft_obj = EmailCampaign.objects.create(
                        title=title,
                        subject=subject,
                        body=body,
                        audience_type=audience_type,
                        event_id_snapshot=selected_event.id if selected_event else None,
                        event_name_snapshot=str(selected_event) if selected_event else "",
                        created_by=request.user,
                        status="draft",
                    )

                selected_draft_id = str(draft_obj.id)
                messages.success(request, f'Draft "{draft_obj.title or draft_obj.subject}" saved.')

        elif action in ["preview", "send_test", "send"]:
            if not subject:
                messages.error(request, "Subject is required.")
                preview_mode = True
            elif not body:
                messages.error(request, "Email body is required.")
                preview_mode = True

            if action in ["preview", "send_test"] and not chosen_rows and audience:
                chosen_rows = [audience[0]]

            if action == "preview":
                preview_mode = True

                sample_row = chosen_rows[0] if chosen_rows else None
                subscriber = sample_row["subscriber"] if sample_row else None

                context = build_campaign_context(
                    subscriber=subscriber,
                    event=selected_event,
                    email=sample_row["email"] if sample_row else "",
                )

                rendered_subject = render_campaign_content(subject, context)
                rendered_body = render_campaign_content(body, context)
                fake_unsubscribe_url = request.build_absolute_uri("#unsubscribe-preview")

                preview_subject = rendered_subject
                preview_html = build_marketing_email_html(
                    rendered_body=rendered_body,
                    unsubscribe_url=fake_unsubscribe_url,
                    recipient_name=context.get("first_name") or context.get("full_name") or "",
                )

            elif action == "send_test":
                preview_mode = True

                test_to = getattr(request.user, "email", "") or test_email
                if not test_to:
                    messages.error(request, "No test email found. Add an email to your account or type one in.")
                else:
                    sample_row = chosen_rows[0] if chosen_rows else None
                    subscriber = sample_row["subscriber"] if sample_row else None
                    subscriber = ensure_subscriber_unsubscribe_token(subscriber)

                    context = build_campaign_context(
                        subscriber=subscriber,
                        event=selected_event,
                        email=test_to,
                    )

                    rendered_subject = render_campaign_content(subject, context)
                    rendered_body = render_campaign_content(body, context)
                    fake_unsubscribe_url = request.build_absolute_uri("#unsubscribe-preview")

                    preview_subject = rendered_subject
                    preview_html = build_marketing_email_html(
                        rendered_body=rendered_body,
                        unsubscribe_url=fake_unsubscribe_url,
                        recipient_name=context.get("first_name") or context.get("full_name") or "",
                    )

                    try:
                        msg = EmailMultiAlternatives(
                            subject=rendered_subject,
                            body=strip_tags(rendered_body),
                            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                            to=[test_to],
                        )
                        msg.attach_alternative(preview_html, "text/html")
                        msg.send()
                        messages.success(request, f"Test email sent to {test_to}.")
                    except Exception as exc:
                        messages.error(request, f"Test email failed: {exc}")

            elif action == "send":
                if not chosen_rows:
                    messages.error(request, "Select at least one recipient.")
                else:
                    campaign = EmailCampaign.objects.create(
                        title=title,
                        subject=subject,
                        body=body,
                        audience_type=audience_type,
                        event_id_snapshot=selected_event.id if selected_event else None,
                        event_name_snapshot=str(selected_event) if selected_event else "",
                        created_by=request.user,
                        status="sending",
                        total_recipients=len(chosen_rows),
                    )

                    sent_count = 0
                    failed_count = 0

                    for row in chosen_rows:
                        subscriber = row["subscriber"]
                        subscriber = ensure_subscriber_unsubscribe_token(subscriber)

                        recipient = EmailCampaignRecipient.objects.create(
                            campaign=campaign,
                            subscriber=subscriber,
                            email=row["email"],
                            first_name=row.get("first_name", ""),
                            last_name=row.get("last_name", ""),
                            was_selected=True,
                        )

                        try:
                            context = build_campaign_context(
                                subscriber=subscriber,
                                event=selected_event,
                                email=row["email"],
                            )

                            rendered_subject = render_campaign_content(campaign.subject, context)
                            rendered_body = render_campaign_content(campaign.body, context)

                            unsubscribe_url = request.build_absolute_uri(
                                reverse("control:subscribers:unsubscribe", args=[subscriber.unsubscribe_token])
                            )

                            html_body = build_marketing_email_html(
                                rendered_body=rendered_body,
                                unsubscribe_url=unsubscribe_url,
                                recipient_name=context.get("first_name") or context.get("full_name") or "",
                            )

                            msg = EmailMultiAlternatives(
                                subject=rendered_subject,
                                body=strip_tags(rendered_body),
                                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                                to=[row["email"]],
                            )
                            msg.attach_alternative(html_body, "text/html")
                            msg.send()

                            recipient.sent_at = timezone.now()
                            recipient.save(update_fields=["sent_at"])
                            sent_count += 1

                        except Exception as exc:
                            recipient.failed_at = timezone.now()
                            recipient.error_message = str(exc)
                            recipient.save(update_fields=["failed_at", "error_message"])
                            failed_count += 1

                    campaign.sent_count = sent_count
                    campaign.failed_count = failed_count

                    if sent_count and failed_count:
                        campaign.status = "partial"
                    elif sent_count and not failed_count:
                        campaign.status = "sent"
                    else:
                        campaign.status = "failed"

                    campaign.sent_at = timezone.now()
                    campaign.save(update_fields=["sent_count", "failed_count", "status", "sent_at"])

                    failure_messages = list(
                        campaign.recipients
                        .exclude(error_message="")
                        .values_list("email", "error_message")
                    )

                    for email, error in failure_messages[:10]:
                        messages.error(request, f"{email}: {error}")

                    messages.success(request, f"Campaign finished. Sent: {sent_count}. Failed: {failed_count}.")

                    if audience_type == "ticket_buyers" and selected_event:
                        return redirect(
                            reverse("control:subscribers:audience_outreach") + f"?audience_type=ticket_buyers&event_id={selected_event.id}"
                        )
                    return redirect(reverse("control:subscribers:audience_outreach") + "?audience_type=subscribers")

        templates = EmailTemplate.objects.all().order_by("title")
        drafts = EmailCampaign.objects.filter(status="draft").order_by("-created_at")

    return render(request, "subscribers/audience_outreach.html", {
        "events": events,
        "templates": templates,
        "drafts": drafts,
        "audience_type": audience_type,
        "selected_event": selected_event,
        "audience": audience,
        "preview_html": mark_safe(preview_html) if preview_html else "",
        "preview_subject": preview_subject,
        "preview_body": preview_body,
        "preview_mode": preview_mode,
        "available_tags": [
            "{{ first_name }}",
            "{{ last_name }}",
            "{{ full_name }}",
            "{{ email }}",
            "{{ event_name }}",
            "{{ event_date }}",
        ],
        "draft_title": draft_title_value,
        "draft_subject": draft_subject_value,
        "draft_body": draft_body_value,
        "draft_test_email": draft_test_email_value,
        "selected_template_id": selected_template_id,
        "selected_draft_id": selected_draft_id,
    })

def unsubscribe(request, token):
    subscriber = get_object_or_404(Subscriber, unsubscribe_token=token)

    if request.method == "POST":
        subscriber.unsubscribe()
        return render(request, "subscribers/unsubscribe_done.html", {"subscriber": subscriber})

    return render(request, "subscribers/unsubscribe.html", {"subscriber": subscriber})

@staff_member_required
def sync_ticket_buyers(request):
    sync_ticket_buyers_to_subscribers()
    messages.success(request, "Ticket buyers synced into subscribers.")
    return redirect(reverse("control:subscribers:audience_outreach") + "?audience_type=subscribers")

