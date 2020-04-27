from django.contrib.auth.models import User, Group
from rest_framework import serializers

class OverlapSerializer(serializers.Serializer):
    """
    Overlap Post API endpoint.
    """

    x = serializers.ListField()
    y = serializers.ListField()

class SentenceSerializer(serializers.Serializer):
    """
    Sentence Post API endpoint.
    """

    pmid = serializers.CharField()    

class EnrichSerializer(serializers.Serializer):
    """
    Enrich Post API endpoint.
    """

    text = serializers.ListField()
