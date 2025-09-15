from django import forms
from .models import Subscriber, Tag

class SubscriberForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = ["email", "first_name", "last_name", "phone",
                  "city", "state", "country", "birthday", "tags"]

class BulkSendForm(forms.Form):
    state = forms.CharField(required=False)
    birthday_month = forms.IntegerField(min_value=1, max_value=12, required=False)
    tags = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)
    subject = forms.CharField(max_length=200)
    body = forms.CharField(widget=forms.Textarea)
