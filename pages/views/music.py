from django.shortcuts import render
from ..models import Release

def music(request):
    releases = Release.objects.prefetch_related("tracks").all()
    return render(request, "pages/music.html", {"releases": releases})
