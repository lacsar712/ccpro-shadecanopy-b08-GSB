from datetime import timedelta

from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ClimateLog, Greenhouse, IrrigationCycle, Zone
from .serializers import (
    ClimateLogSerializer,
    GreenhouseSerializer,
    IrrigationCycleSerializer,
    ZoneSerializer,
)


class GreenhouseViewSet(viewsets.ModelViewSet):
    queryset = Greenhouse.objects.annotate(zone_count=Count("zones")).all()
    serializer_class = GreenhouseSerializer


class ZoneViewSet(viewsets.ModelViewSet):
    serializer_class = ZoneSerializer

    def get_queryset(self):
        qs = Zone.objects.select_related("greenhouse").all()
        greenhouse_id = self.request.query_params.get("greenhouseId")
        status = self.request.query_params.get("status")
        if greenhouse_id:
            qs = qs.filter(greenhouse_id=greenhouse_id)
        if status:
            qs = qs.filter(status=status)
        return qs


class ClimateVoidSerializer(drf_serializers.Serializer):
    reason = drf_serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_reason(self, value):
        reason = (value or "").strip()
        if reason and len(reason) < 6:
            raise drf_serializers.ValidationError("作废原因去空白后至少 6 个字")
        return reason


class ClimateLogViewSet(viewsets.ModelViewSet):
    serializer_class = ClimateLogSerializer

    def get_queryset(self):
        qs = ClimateLog.objects.select_related("zone", "zone__greenhouse").all()
        zone_id = self.request.query_params.get("zoneId")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        # 默认列表不含已作废行；显式 includeVoided=true 时返回全部并打标。
        if self.request.query_params.get("includeVoided") != "true":
            qs = qs.filter(voided_at__isnull=True)
        return qs

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        # 不经默认 queryset（默认已排除作废行），否则重复作废会得到 404 而非 409。
        log = get_object_or_404(ClimateLog, pk=pk)
        if log.voided_at is not None:
            return Response(
                {"detail": "该气候记录已作废，不能重复作废"},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = ClimateVoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        log.voided_at = timezone.now()
        log.void_reason = serializer.validated_data.get("reason", "")
        log.save(update_fields=["voided_at", "void_reason"])
        return Response(
            ClimateLogSerializer(log).data, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="stats/void")
    def void_stats(self, request):
        # 统计口径与列表一致：可带 zoneId 过滤。
        qs = ClimateLog.objects.all()
        zone_id = request.query_params.get("zoneId")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        voided_count = qs.filter(voided_at__isnull=False).count()
        valid_count = qs.filter(voided_at__isnull=True).count()
        return Response(
            {"voidedTotal": voided_count, "validTotal": valid_count}
        )


class IrrigationCycleViewSet(viewsets.ModelViewSet):
    serializer_class = IrrigationCycleSerializer

    def get_queryset(self):
        qs = IrrigationCycle.objects.select_related("zone", "zone__greenhouse").all()
        zone_id = self.request.query_params.get("zoneId")
        status = self.request.query_params.get("status")
        if zone_id:
            qs = qs.filter(zone_id=zone_id)
        if status:
            qs = qs.filter(status=status)
        return qs


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    now = timezone.now()
    since_24h = now - timedelta(hours=24)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    data = {
        "greenhouseCount": Greenhouse.objects.count(),
        "growingZoneCount": Zone.objects.filter(status=Zone.STATUS_GROWING).count(),
        "climateLogLast24h": ClimateLog.objects.filter(
            recorded_at__gte=since_24h, voided_at__isnull=True
        ).count(),
        "irrigationScheduledToday": IrrigationCycle.objects.filter(
            status=IrrigationCycle.STATUS_SCHEDULED,
            start_at__gte=today_start,
            start_at__lt=today_end,
        ).count(),
    }
    return Response(data)
