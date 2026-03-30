from django.shortcuts import render
from django.http import FileResponse, Http404
import os


def index(request):
    return render(request, 'map_app/index.html')


def service_worker(request):
    """Serve the service worker at /sw.js with the required Service-Worker-Allowed header."""
    sw_path = os.path.join(
        os.path.dirname(__file__), 'static', 'map_app', 'sw.js'
    )
    if not os.path.exists(sw_path):
        raise Http404('Service worker not found')
    response = FileResponse(open(sw_path, 'rb'), content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response
