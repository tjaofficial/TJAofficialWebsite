from django.db.models import Sum, Q
from equipment.models import EventEquipment
from .models import EventChecklist, ChecklistTemplate, EventChecklistItem

def equipment_reserved_qty(equipment, start, end, exclude_event_id=None):
    """
    Sum qty reserved for this equipment across events that overlap [start, end).
    Optionally exclude a specific event (e.g., when editing).
    """
    q = EventEquipment.objects.filter(equipment=equipment,
                                      event__start__lt=end,
                                      event__end__gt=start)
    if exclude_event_id:
        q = q.exclude(event_id=exclude_event_id)
    return q.aggregate(Sum("qty"))["qty__sum"] or 0

def ensure_event_checklist(event):
    cl, created = EventChecklist.objects.get_or_create(event=event)
    if created and not cl.items.exists():
        # seed from active template
        tpl = ChecklistTemplate.objects.filter(is_active=True).first()
        if tpl:
            cl.template_used = tpl
            cl.save(update_fields=["template_used"])
            EventChecklistItem.objects.bulk_create([
                EventChecklistItem(checklist=cl, title=it.title, order=idx, is_required=it.is_required)
                for idx, it in enumerate(tpl.items.all())
            ])
    return cl



