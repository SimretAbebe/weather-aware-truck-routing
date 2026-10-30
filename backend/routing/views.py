import logging
from concurrent.futures import ThreadPoolExecutor

import requests
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .presenters import present_analysis
from .serializers import AnalyzeRequestSerializer
from .services.analysis import analyze_routes
from .services.geocode import search_places
from .services.heatmap import build_heatmap
from .services.routing_provider import get_route_options
from .services.weather import fetch_hourly

log = logging.getLogger(__name__)


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def geocode(request):
    q = request.query_params.get("q", "").strip()
    if len(q) < 3:
        return Response({"results": []})
    try:
        return Response({"results": search_places(q)})
    except requests.RequestException:
        return Response({"detail": "Geocoding service unavailable."}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(["POST"])
def analyze(request):
    s = AnalyzeRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    origin = (d["origin"]["lon"], d["origin"]["lat"])
    dest = (d["destination"]["lon"], d["destination"]["lat"])

    routes = get_route_options(origin, dest)
    if not routes:
        return Response({"detail": "No drivable route found between those points."},
                        status=status.HTTP_404_NOT_FOUND)

    # Route analysis and heatmap fetch weather independently, so run them in parallel.
    with ThreadPoolExecutor(max_workers=2) as pool:
        fa = pool.submit(analyze_routes, routes, d["departure"], d["load_lb"], d["interval_mi"], fetch_hourly)
        fh = pool.submit(build_heatmap, routes, d["departure"], d["load_lb"], fetch_hourly)
        try:
            analyses = fa.result()
        except requests.RequestException as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            log.error("weather fetch failed: %s (status=%s)", repr(e), code)
            return Response(
                {"detail": f"Weather service unavailable (cause: {code or type(e).__name__}). Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )   
        try:
            heatmap = fh.result()
        except Exception:  # the heatmap is secondary; don't lose the analysis over it
            log.exception("heatmap failed")
            heatmap = None

    return Response({
        "routes": [present_analysis(a) for a in analyses],
        "heatmap": heatmap,
        "requested_routes": 3,
    })