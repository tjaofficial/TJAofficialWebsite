from django.shortcuts import render
from ..models import Release

def music(request):
    releases = Release.objects.prefetch_related("tracks").all()
    return render(request, "pages/music.html", {"releases": releases})

def exclusive_music(request):
    releases = Release.objects.prefetch_related("tracks").filter(is_public=False)
    if not releases.exists():
        releases = False
    return render(request, "pages/exclusive_music.html", {"releases": releases})