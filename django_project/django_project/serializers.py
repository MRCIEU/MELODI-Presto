from django.contrib.auth.models import User, Group
from rest_framework import serializers


class OverlapSerializer(serializers.Serializer):
    """
    Overlap Post API endpoint.
    """

    x = serializers.ListField(child=serializers.CharField(min_length=2))
    y = serializers.ListField(child=serializers.CharField(min_length=2))


class SentenceSerializer(serializers.Serializer):
    """
    Sentence Post API endpoint.
    """

    pmid = serializers.CharField(required=True)


class EnrichSerializer(serializers.Serializer):
    """
    Enrich Post API endpoint.
    """

    query = serializers.CharField(min_length=2)
