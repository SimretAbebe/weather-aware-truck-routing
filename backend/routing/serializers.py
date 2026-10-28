from datetime import datetime, timedelta, timezone

from rest_framework import serializers

from .services.analysis import VALID_INTERVALS
from .services.routing_provider import haversine_mi

MAX_DAYS_AHEAD = 14  # keeps the 48h heatmap inside Open-Meteo's 16-day window


class PointSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)


class AnalyzeRequestSerializer(serializers.Serializer):
    origin = PointSerializer()
    destination = PointSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.IntegerField(min_value=1, max_value=120_000)
    interval_mi = serializers.ChoiceField(choices=VALID_INTERVALS, default=25)

    def validate_interval_mi(self, value):
        return int(value)

    def validate_departure(self, value: datetime):
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        earliest = max(now - timedelta(hours=1), today)
        if value < earliest:
            raise serializers.ValidationError("Departure can't be in the past.")
        if value > now + timedelta(days=MAX_DAYS_AHEAD):
            raise serializers.ValidationError(
                f"Departure must be within {MAX_DAYS_AHEAD} days (forecast limit)."
            )
        return value

    def validate(self, data):
        o, d = data["origin"], data["destination"]
        if haversine_mi((o["lon"], o["lat"]), (d["lon"], d["lat"])) < 1:
            raise serializers.ValidationError("Origin and destination are too close together.")
        return data