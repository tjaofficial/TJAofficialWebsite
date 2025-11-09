from django import forms
from .models import Event, Venue, TechPerson, EventTechAssignment, EventMedia
from django.utils.timezone import localtime

# forms.py
class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name","is_tour_stop","is_21_plus","start","end","venue",
                  "afterparty_info","meet_greet_info","cover_image","flyer","published"]
        widgets = {
            "start": forms.DateTimeInput(attrs={"type":"datetime-local", "class":"control"}, format="%Y-%m-%dT%H:%M"),
            "end":   forms.DateTimeInput(attrs={"type":"datetime-local", "class":"control"}, format="%Y-%m-%dT%H:%M"),
            "venue": forms.Select(attrs={"class": "control", "id": "venue-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # accept browser format
        self.fields["start"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end"].input_formats   = ["%Y-%m-%dT%H:%M"]


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["name","address","city","state","country","capacity",
                  "owner_name","owner_email","entertainment_manager","entertainment_email","hours"]


class TechPersonForm(forms.ModelForm):
    class Meta:
        model = TechPerson
        fields = ["name","role","city","state","email","phone","rate_cents","notes","active"]

class EventTechAssignForm(forms.ModelForm):
    class Meta:
        model = EventTechAssignment
        fields = ["person","role","rate_cents","confirmed","notes"]

class EventMediaForm(forms.ModelForm):
    class Meta:
        model = EventMedia
        fields = ["kind","image","video_url","caption"]
