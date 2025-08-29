from django.shortcuts import render
from ..models import Video

def videos(request):
    vids = Video.objects.filter(is_public=True)
    return render(request, "pages/videos.html", {"videos": vids})
