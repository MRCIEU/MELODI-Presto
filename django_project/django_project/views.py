from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.core.cache import cache
from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import views
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.views.decorators.csrf import csrf_exempt
from django_project.serializers import (
    OverlapSerializer,
    EnrichSerializer,
    SentenceSerializer,
)
import config
import requests
import time
import json
import logging

from string import punctuation
from scipy.spatial import distance
import numpy as np
import os

# logging
logging.basicConfig(
    format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p", level=logging.INFO
)
logger = logging.getLogger("debug_logger")
es_logger = logging.getLogger("elastic_logger")

from scripts.pubmed_functions import pubmed_query_to_pmids, get_pubmed_info
from scripts.semmed_functions import *

api_url = config.api_url
root_url = config.root_url

deploy = config.DEPLOYMENT
if deploy == "prod":
    print("#### Running in production mode ####\n")
else:
    print("#### Running in development mode ####\n")

#### Web


def index(request):
    template = loader.get_template("django_project/index.html")
    context = {"nbar": "home", "root_url": root_url}
    return HttpResponse(template.render(context, request))


def about(request):
    template = loader.get_template("django_project/about.html")
    context = {"nbar": "about"}
    return HttpResponse(template.render(context, request))


def app(request):
    template = loader.get_template("django_project/app.html")
    context = {"nbar": "app"}
    return HttpResponse(template.render(context, request))


def enrich(request):
    template = loader.get_template("django_project/enrich.html")
    context = {"nbar": "app", "api_url": api_url}
    return HttpResponse(template.render(context, request))


def overlap(request):
    template = loader.get_template("django_project/overlap.html")
    context = {"nbar": "app", "api_url": api_url}
    return HttpResponse(template.render(context, request))


def sentence(request, pmid=""):
    template = loader.get_template("django_project/sentence.html")
    context = {"nbar": "app", "api_url": api_url, "pmid": pmid}
    return HttpResponse(template.render(context, request))


### API


@api_view(["GET"])
def StatusView(request):
    """
    API endpoint for status of API .

    Returns true/false
    """
    return Response(True)


@swagger_auto_schema(methods=["post"], request_body=SentenceSerializer)
@api_view(["POST"])
def SentencePostView(request):
    """
    API endpoint for SemMedDB Sentence return for a given PubMed ID, e.g. 23715093.

    Returns JSON:
    - count: The number of records returned,
    - data: The records:
      - PREDICATION_ID: the SemMedDB predication ID,
      - SENTENCE_ID: Auto-generated primary key for each sentence,
      - PMID: The PubMed identifier of the citation to which the sentence belongs,
      - PREDICATE: The string representation of each predicate (for example TREATS, PROCESS_OF),
      - SUBJECT_CUI: The CUI of the subject of the predication,
      - SUBJECT_NAME: The preferred name of the subject of the predication,
      - SUBJECT_SEMTYPE: The semantic type of the subject of the predication,
      - SUBJECT_NOVELTY: The novelty of the subject of the predication,
      - OBJECT_CUI: The CUI of the object of the predication,
      - OBJECT_NAME: The preferred name of the object of the predication,
      - OBJECT_SEMTYPE: The semantic type of the object of the predication,
      - OBJECT_NOVELTY: The novelty of the object of the predication,
      - SUB_PRED_OBJ: ID created from combindata of subject name:predicate:object_name,
      - NORMALIZED_SECTION_HEADER: Normalized section header name of structured abstract (from Version 3.1),
      - SECTION_HEADER: Section header name of structured abstract (from Version 3.1),
      - SENT_START_INDEX: The starting index in the sentence for the triple,
      - SENTENCE: The actual string or text of the sentence
      - TYPE: 'ti' for the title of the citation, 'ab' for the abstract,
      - NUMBER: The location of the sentence within the title or abstract,
      - SENT_END_INDEX: The starting index in the sentence for the triple
    """
    if request.method == "POST":
        data = json.loads(request.body)
        serializer = SentenceSerializer(data=data)
        if serializer.is_valid():
            pmid = data["pmid"]
            logger.info("Sentence query Post: " + pmid)
            es_logger.info("Sentence POST " + str(pmid))
            # get sentence data
            filterData = {"term": {"PMID": pmid}}
            time1, count1, res1 = run_standard_query(
                filterData=filterData,
                index=config.semmed_sentence_index + "," + config.semmed_citation_index,
                size=1000,
            )
            # get sentence IDs and CITATION data
            sent_dic = {}
            citation_dic = {}
            # logger.debug(res1)
            for r in res1:
                if r["_index"] == config.semmed_citation_index:
                    citation_dic[str(r["_source"]["PMID"])] = r["_source"]
                if r["_index"] == config.semmed_sentence_index:
                    sent_dic[r["_source"]["SENTENCE_ID"]] = r["_source"]
            filterData = {"terms": {"SENTENCE_ID": list(sent_dic.keys())}}
            # logger.debug(filterData)
            time2, count2, res2 = run_standard_query(
                filterData=filterData, index=config.semmed_predicate_index, size=1000
            )
            # logger.debug(res2)
            # stitch them together
            final_res = []
            for r in res2:
                tmp_dic = r["_source"]
                sent_id = r["_source"]["SENTENCE_ID"]
                pubmed_id = str(r["_source"]["PMID"])
                if sent_id in sent_dic:
                    tmp_dic.update(sent_dic[sent_id])
                    # this doesn't work as start and end appear to map to the abstract
                    # sentence_section = sent_dic[sent_id]['SENTENCE'][int(sent_dic[sent_id]['SENT_START_INDEX'])-2:int(sent_dic[sent_id]['SENT_END_INDEX'])-2]
                    # tmp_dic.update({'SENTENCE_SECTION':sentence_section})
                if pubmed_id in citation_dic:
                    tmp_dic.update(citation_dic[pubmed_id])
                final_res.append(tmp_dic)
            # logger.info(pmid)
            if pmid in citation_dic:
                # get title and abstract
                pubmed_data = get_pubmed_info([pmid])
                # logger.info(pubmed_data)
                # print(final_res)
                returnData = {
                    "count": count2,
                    "data": final_res,
                    "title": pubmed_data["title"],
                }
            else:
                returnData = {
                    "count": 0,
                    "data": final_res,
                    "title": "NA",
                    "Error": pmid + " not in database",
                }
        else:
            returnData = serializer.errors
    return Response(returnData)


@swagger_auto_schema(methods=["post"], request_body=OverlapSerializer)
@api_view(["POST"])
def OverlapPostView(request):
    """
    API endpoint for returning overlapping triples. Accepts two lists of query terms, x and y, e.g. ['NF1','MALAT1','NEAT2'] amd ['neuroblastoma','lung cancer']

    Returns JSON:
    - count: The number of records returned,
    - data: The records
      - triple_x: ID created from combindata of subject name:predicate:object_name (query X),
      - subject_name_x: The preferred name of the subject of the predication (query x),
      - subject_type_x: The semantic type of the subject of the predication (query x),
      - subject_id_x: The Concept Unique Identifier (CUI) of the subject of the predication (query x),
      - predicate_x: The string representation of each predicate (for example TREATS, PROCESS_OF) (query x),
      - object_name_x: The preferred name of the object of the predication (query x),
      - object_type_x: The semantic type of the object of the predication (query x),
      - object_id_x: The Concept Unique Identifier (CUI) of the object of the predication (query x),
      - localCount_x: The triple count for a given triple from the search query (query x),
      - localTotal_x: The total number of triples from the search query (query x),
      - globalCount_x: The global count for a given triple (query x),
      - globalTotal_x: The global number of triples (query x),
      - odds_x: Odds ration from the Fisher's Exact Test (query x),
      - pval_x: P-value from the Fisher's Exact Test (query x),
      - pmids_x: The PubMed IDs from which the triples were derived (query x),
      - set_x: The query name used (query x),
      - triple_y: ID created from combindata of subject name:predicate:object_name (query y),
      - subject_name_y: The preferred name of the subject of the predicatio (query y),
      - subject_type_y: The semantic type of the subject of the predication (query y),
      - subject_id_y: The Concept Unique Identifier (CUI) of the subject of the predication (query y),
      - predicate_y: The string representation of each predicate (for example TREATS, PROCESS_OF) (query y),
      - object_name_y: The preferred name of the object of the predication (query y),
      - object_type_y: The semantic type of the object of the predication (query y),
      - object_id_y: The Concept Unique Identifier (CUI) of the object of the predication (query y),
      - localCount_y: The triple count for a given triple from the search query (query y),
      - localTotal_y: The total number of triples from the search query (query y),
      - globalCount_y: The global count for a given triple (query y),
      - globalTotal_y: The global number of triples (query y),
      - odds_y: Odds ration from the Fisher's Exact Test (query y),
      - pval_y: P-value from the Fisher's Exact Test (query y),
      - pmids_y: The PubMed IDs from which the triples were derived (query y),
      - set_y: The query name used (query y)
    """
    if request.method == "POST":
        data = json.loads(request.body)
        serializer = OverlapSerializer(data=data)
        if serializer.is_valid():
            # print(data)
            logger.info("Overlap Query Post")
            x = [x.strip().replace(" ", "_").lower() for x in data["x"]]
            y = [x.strip().replace(" ", "_").lower() for x in data["y"]]
            logger.info("Overlap Get x: " + str(x))
            logger.info("Overlap Get y: " + str(y))
            es_logger.info("Overlap POST " + str(x) + ":" + str(y))
            sem_trip_dic = {}
            for e in x:
                logger.info("pub_sem: " + e)
                pub_sem(e, sem_trip_dic)
            for o in y:
                logger.info("pub_sem: " + o)
                pub_sem(o, sem_trip_dic)
            joinDic = compare_sem_df(x, y)
            returnData = joinDic
        else:
            returnData = serializer.errors
        return Response(returnData)


@swagger_auto_schema(methods=["post"], request_body=EnrichSerializer)
@api_view(["POST"])
def EnrichPostView(request):
    """
    API endpoint for triple enrichment. Accepts a single biomedical term query, e.g. "PCSK9", "NF1", "MALAT1", "Sleep duration"

    Returns JSON:
      - query: The query term used,
      - triple: ID created from combindata of subject name:predicate:object_name,
      - subject_name: The preferred name of the subject of the predication,
      - subject_type: The semantic type of the subject of the predication,
      - subject_id: The Concept Unique Identifier (CUI) of the subject of the predication,
      - predicate: The string representation of each predicate (for example TREATS, PROCESS_OF),
      - object_name: The preferred name of the object of the predication,
      - object_type: The semantic type of the object of the predication,
      - object_id: The Concept Unique Identifier (CUI) of the object of the predication,
      - localCount: The triple count for a given triple from the search query,
      - localTotal: The total number of triples from the search query,
      - globalCount: The global count for a given triple,
      - globalTotal: The global number of triples,
      - odds: Odds ration from the Fisher's Exact Test,
      - pval: P-value from the Fisher's Exact Test,
      - pmids: The PubMed IDs from which the triples were derived
    """
    if request.method == "POST":
        data = json.loads(request.body)
        serializer = EnrichSerializer(data=data)
        if serializer.is_valid():
            logger.info("Enrich Query Post")
            text = data["query"].replace(" ", "_").lower()
            logger.info("Enrich Text: " + str(text))
            sem_trip_dic = {}
            logger.info("pub_sem: " + text + " " + str(len(text)))
            d = pub_sem(text, sem_trip_dic)
            enrichData = d
            es_logger.info("Enrich POST " + str(text))
            if d is None:
                logger.info("no results")
                returnData = []
            else:
                returnData = enrichData
        else:
            returnData = serializer.errors
        return Response(returnData)
