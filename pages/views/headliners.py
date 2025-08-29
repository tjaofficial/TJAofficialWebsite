from django.shortcuts import render

def headliners(request):
    return render(request, 'pages/headliners.html')
