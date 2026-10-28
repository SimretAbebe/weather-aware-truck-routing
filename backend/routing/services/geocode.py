import requests

PHOTON_URL = "https://photon.komoot.io/api/"
HEADERS = {"User-Agent": "weather-aware-truck-routing/1.0"}


def search_places(query: str, limit: int = 5) -> list[dict]:
    r = requests.get(
        PHOTON_URL,
        params={"q": query, "limit": limit, "lang": "en"},
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    places = []
    for f in r.json().get("features", []):
        p = f.get("properties", {})
        lon, lat = f["geometry"]["coordinates"]
        name = p.get("name")
        parts = [name, p.get("city") if p.get("city") != name else None, p.get("state"), p.get("country")]
        label = ", ".join(x for x in parts if x)
        if label:
            places.append({"label": label, "lat": lat, "lon": lon})
    return places