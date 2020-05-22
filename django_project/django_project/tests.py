from django.urls import include, path, reverse
from rest_framework.test import APITestCase, URLPatternsTestCase


class APITests(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path("django_project/", include("django_project.urls")),
    ]

    def test_enrich(self):
        """
        Enrich test
        """
        query = "pcsk9"
        url = "/django_project/api/enrich/"
        data = {"query": query}
        response = self.client.post(url, data, format="json")
        self.assertEqual(len(response.data), 333)

    def test_overlap(self):
        """
        Overlap test
        """
        query1 = "pcsk9"
        query2 = "marfan syndrome"
        url = "/django_project/api/overlap/"
        data = {"x": [query1], "y": [query2]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(len(response.data["data"]), 25)

    def test_sentence(self):
        """
        Overlap test
        """
        pmid = "23715093"
        url = "/django_project/api/sentence/"
        data = {"pmid": pmid}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.data["count"], 5)
