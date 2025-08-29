from django.shortcuts import render

def links(request):
    return render(request, 'pages/links.html')