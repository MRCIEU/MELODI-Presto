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
from django_project.serializers import *
import config
import requests
import time
import json
import logging

from string import punctuation
from scipy.spatial import distance
import numpy as np
import os

#logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)
logger = logging.getLogger('debug_logger')
es_logger=logging.getLogger('elastic_logger')

from scripts.pubmed_functions import pubmed_query_to_pmids
from scripts.es_functions import check_medline_ngram_index, get_pubmed_data_from_elastic
from scripts.semmed_functions import *

api_url=config.api_url

deploy=config.DEPLOYMENT
if deploy=="prod":
    print('#### Running in production mode ####\n')
else:
    print('#### Running in development mode ####\n')

#### Web

def index(request):
    template = loader.get_template('django_project/index.html')
    context = {
      'index': {
        'api': 'API',
        'app': 'App',
        'repo': 'GitHub'
      }
    }
    return HttpResponse(template.render(context, request))

def app(request):
    template = loader.get_template('django_project/app.html')
    context = {}
    return HttpResponse(template.render(context, request))

def overlap(request):
    template = loader.get_template('django_project/overlap.html')
    context = {'api_url':api_url}
    return HttpResponse(template.render(context, request))

### API

@api_view(['GET'])
def StatusView(request):
    return Response(True)


@swagger_auto_schema(methods=['post'], request_body=SentenceSerializer)
@api_view(['POST'])
def SentencePostView(request):
    """
    API endpoint for SemMedDB Sentence return for a given PubMed ID, e.g. 23715093.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        if 'pmid' in data:
            pmid = data['pmid']
            logger.info('Sentence query Post: '+pmid)
            es_logger.info('Sentence POST '+str(pmid))
            #get sentence data 
            filterData={"term":{"PMID":pmid}}
            time1,count1,res1 = run_standard_query(filterData=filterData,index=config.semmed_sentence_index,size=1000)
            #get sentence IDs
            sent_dic = {}
            for r in res1:
                sent_dic[r['_source']['SENTENCE_ID']]=r['_source']
            filterData={"terms":{"SENTENCE_ID":list(sent_dic.keys())}}
            time2,count2,res2 = run_standard_query(filterData=filterData,index=config.semmed_index,size=1000)
            #stitch them together
            final_res=[]
            for r in res2:
                tmp_dic=r['_source']
                sent_id = r['_source']['SENTENCE_ID']
                if sent_id in sent_dic:
                    tmp_dic.update(sent_dic[sent_id])
                    #this doesn't work as start and end appear to map to the abstract
                    #sentence_section = sent_dic[sent_id]['SENTENCE'][int(sent_dic[sent_id]['SENT_START_INDEX'])-2:int(sent_dic[sent_id]['SENT_END_INDEX'])-2]
                    #tmp_dic.update({'SENTENCE_SECTION':sentence_section})
                final_res.append(tmp_dic)
            #print(final_res)
            returnData={'count':count2,'results':final_res}
        else:
            returnData = ['Error: need a PubMed ID']
    return Response(returnData)

@swagger_auto_schema(methods=['post'], request_body=OverlapSerializer)
@api_view(['POST'])
def OverlapPostView(request):
    """
    API endpoint for MELODI style overlap return. Accepts two lists of query terms, x and y, e.g. ['NF1','MALAT1','NEAT2'] amd ['neuroblastoma','lung cancer']
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        #print(data)
        logger.info('Overlap Query Post')
        if 'x' in data and 'y' in data:
            x = [x.strip().replace(' ','_').lower() for x in data['x']]
            y = [x.strip().replace(' ','_').lower() for x in data['y']]
            logger.info('Overlap Get x: '+str(x))
            logger.info('Overlap Get y: '+str(y))
            es_logger.info('Overlap POST '+str(x)+':'+str(y))
            sem_trip_dic={}
            for e in x:
                logger.info('pub_sem: '+e)
                pub_sem(e,sem_trip_dic)
            for o in y:
                logger.info('pub_sem: '+o)
                pub_sem(o,sem_trip_dic)
            joinDic = compare_sem_df(x,y)
            return Response(joinDic)
        else:
            logger.info('missing data')
            return Response('')

@swagger_auto_schema(methods=['post'], request_body=EnrichSerializer)
@api_view(['POST'])
def EnrichPostView(request):
    """
    API endpoint for MELODI style SemMedDB triple enrichment.
    Accepts a list of biomedical terms.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        serializer = EnrichSerializer(data=data)
        if serializer.is_valid():
            logger.info('Enrich Query Post')
            if 'query' in data:
                text = [x.replace(' ','_').lower() for x in data['query']]
                logger.info('Enrich Text: '+str(text))
                sem_trip_dic={}
                enrichDic={}
                for e in text:
                    logger.info('pub_sem: '+e+' '+str(len(e)))
                    enrichDic[e] = pub_sem(e,sem_trip_dic)
                es_logger.info('Enrich POST '+str(text))
                returnData = enrichDic
            else:
                returnData = ['Error: need a list called \'text\''] 
        else:
            returnData = serializer.errors
        return Response(returnData)
