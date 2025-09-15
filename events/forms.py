from django import forms
from .models import Event, Venue

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name","is_tour_stop","start","end","venue","afterparty_info","meet_greet_info","published"]

class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["name","address","city","state","country","capacity",
                  "owner_name","owner_email","entertainment_manager","entertainment_email","hours"]

from django import forms
from .models import Event, Venue, TechPerson, EventTechAssignment, EventMedia

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name","is_tour_stop","start","end","venue","afterparty_info","meet_greet_info","published"]

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
