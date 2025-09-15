from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from events.models import Event
from .models import Equipment, EventEquipment
from .forms import EventEquipmentForm, EquipmentForm
from django.contrib import messages
from django.db.models import Q
from events.utils import equipment_reserved_qty

is_super = user_passes_test(lambda u: u.is_superuser)

@login_required
def event_equipment_list(request, event_id):
    ev = get_object_or_404(Event, pk=event_id)
    rows = ev.equipment_assignments.select_related("equipment").all()
    return render(request, "events/event_equipment_list.html", {"event": ev, "rows": rows})

@login_required
def event_equipment_add(request, event_id):
    ev = get_object_or_404(Event, pk=event_id)

    if request.method=="POST":
        form = EventEquipmentForm(request.POST, event=ev)
        if form.is_valid():
            r = form.save(commit=False)
            r.event = ev
            if r.qty <= 0:
                messages.error(request, "Quantity must be positive.")
            else:
                # availability check
                already = equipment_reserved_qty(r.equipment, ev.start, ev.end, exclude_event_id=None)
                if already + r.qty > r.equipment.qty_total:
                    messages.error(
                        request,
                        f"Not enough '{r.equipment.name}' available for {ev.name}. "
                        f"Reserved in overlapping events: {already}, total inventory: {r.equipment.qty_total}."
                    )
                    return redirect("control:equipment:event_equipment", event_id=ev.id)
                else:
                    r.save()
                    messages.success(request, "Equipment reserved.")
                    return redirect("control:equipment:event_equipment", event_id=ev.id)
    else:
        form = EventEquipmentForm(event=ev)
    return render(request, "events/event_equipment_form.html", {"event": ev, "form": form})

@is_super
def event_equipment_remove(request, event_id, res_id):
    ev = get_object_or_404(Event, pk=event_id)
    r = get_object_or_404(EventEquipment, pk=res_id, event=ev)
    r.delete()
    return redirect("control:equipment:event_equipment", event_id=ev.id)

@login_required
def equipment_list(request):
    q = (request.GET.get("q") or "").strip()
    category = (request.GET.get("category") or "").strip()
    active = (request.GET.get("active") or "").strip()
    min_qty = request.GET.get("min_qty") or ""
    qs = Equipment.objects.all().order_by("category", "name")
    if q: qs = qs.filter(Q(name__icontains=q) | Q(serial__icontains=q))
    if category: qs = qs.filter(category=category)
    if active == "yes": qs = qs.filter(active=True)
    elif active == "no": qs = qs.filter(active=False)
    if min_qty:
        try: qs = qs.filter(qty_total__gte=int(min_qty))
        except ValueError: pass
    ctx = {"rows": qs, "q": {"q": q, "category": category, "active": active, "min_qty": min_qty},
           "categories": Equipment.CATEGORY_CHOICES}
    return render(request, "equipment/equipment_list.html", ctx)

@login_required
def equipment_add(request):
    form = EquipmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Equipment added.")
        return redirect("control:equipment:list")
    return render(request, "equipment/equipment_form.html", {"form": form, "mode": "add"})

@login_required
def equipment_edit(request, pk):
    obj = get_object_or_404(Equipment, pk=pk)
    form = EquipmentForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Equipment updated.")
        return redirect("control:equipment:list")
    return render(request, "equipment/equipment_form.html", {"form": form, "mode": "edit", "obj": obj})

@is_super
def equipment_delete(request, pk):
    obj = get_object_or_404(Equipment, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Equipment deleted.")
        return redirect("control:equipment:list")
    # GET -> confirm page
    return render(request, "equipment/equipment_confirm_delete.html", {"obj": obj})



