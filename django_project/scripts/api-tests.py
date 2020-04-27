import requests
import time
import json
import requests
import pandas as pd
import re

#api_url='http://localhost:8000/api/'
api_url='http://textbase.biocompute.org.uk/api/'

filter_list=[
    '^Blood clot, DVT, bronchitis, emphysema, asthma, rhinitis, eczema, allergy diagnosed by doctor: (.*)',
    '^Cancer code.*?self-reported:\s(.*)',
    '^Contributory (secondary) causes of death: ICD10:\s.*?\s(.*)',
    '^Diagnoses - main ICD10:\s.*?\s(.*)',
    '^Diagnoses - main ICD9:\s.*?\s(.*)',
    '^Diagnoses - secondary ICD10:\s.*?\s(.*)',
    '^Diagnoses - secondary ICD9:\s.*?\s(.*)',
    '^External causes:\s.*?\s(.*)',
    '^Eye problems/disorders: (.*)',
    '^Medication for cholesterol.*?blood pressure.*?diabetes.*?or take exogenous hormones: (.*)',
    '^Medication for cholesterol.*?blood pressure or diabetes: (.*)',
    '^Medication for pain relief.*?constipation.*?heartburn.*?: (.*)',
    '^Medication for smoking cessation, constipation, heartburn, allergies \(pilot\): (.*)',
    '^Non-cancer illness code.*?self-reported:\s(.*)',
    '^Operation code: (.*)',
    '^Operative procedures - main OPCS:\s.*?\s(.*)',
    '^Operative procedures - secondary OPCS:\s.*?\s(.*)',
    '^Treatment/medication code: (.*)',
    '^Type of cancer: ICD10:\s.*?\s(.*)',
]

def pmid_post():
	headers = {'content-type': 'application/x-www-form-urlencoded'}
	params = {'data':['123','234','456','789']}
	url = api_url+'pmid/'
	print(url,params)
	r = requests.post(url, data=params, headers=headers)
	print(r.text)

def orcid_post():
	headers = {'content-type': 'application/x-www-form-urlencoded'}
	params = {'data':'0000-0001-7328-4233'}
	url = api_url+'orcid/'
	print(url,params)
	r = requests.post(url, data=params, headers=headers)
	print(r.text)

testText1="""
Motivation
LD score regression is a reliable and efficient method of using genome-wide association study (GWAS) summary-level results data to estimate the SNP heritability of complex traits and diseases, partition this heritability into functional categories, and estimate the genetic correlation between different phenotypes. Because the method relies on summary level results data, LD score regression is computationally tractable even for very large sample sizes. However, publicly available GWAS summary-level data are typically stored in different databases and have different formats, making it difficult to apply LD score regression to estimate genetic correlations across many different traits simultaneously.

Results
In this manuscript, we describe LD Hub - a centralized database of summary-level GWAS results for 173 diseases/traits from different publicly available resources/consortia and a web interface that automates the LD score regression analysis pipeline. To demonstrate functionality and validate our software, we replicated previously reported LD score regression analyses of 49 traits/diseases using LD Hub; and estimated SNP heritability and the genetic correlation across the different phenotypes. We also present new results obtained by uploading a recent atopic dermatitis GWAS meta-analysis to examine the genetic correlation between the condition and other potentially related traits. In response to the growing availability of publicly accessible GWAS summary-level results data, our database and the accompanying web interface will ensure maximal uptake of the LD score regression methodology, provide a useful database for the public dissemination of GWAS results, and provide a method for easily screening hundreds of traits for overlapping genetic aetiologies.

Availability and Implementation
The web interface and instructions for using LD Hub are available at http://ldsc.broadinstitute.org/
"""

testText2='some text text'

def text_post():
	headers = {'content-type': 'application/x-www-form-urlencoded'}
	params = {'data':testText1,'top':10}
	url = api_url+'text/'
	print(url,params)
	r = requests.post(url, data=params, headers=headers)
	print(r.text)

def get_gwas_filter():
    filterList=[]
    filterFile='data/ukb_id_keep.txt'
    with open(filterFile,'r') as f:
        for line in f:
            filterList.append(line.rstrip().replace('b-','b:'))
    return filterList

def get_gwas_data():
    print('get_gwas_data')
    gwas_api_url='http://api.mrbase.org/get_studies?access_token=null'
    gwas_res = requests.get(gwas_api_url).json()

    #get filter list
    filterList = get_gwas_filter()

    gwasInfo={}
    for g in gwas_res:
        if g['id'].startswith('UKB-b'):
            if g['id'] in filterList:
                gwasInfo[g['id']]=g['trait']
        else:
            gwasInfo[g['id']]=g['trait']

    print(len(gwasInfo),'gwasinfo')
    return gwasInfo

def preprocess_traits(gwasInfo):
    processed={}
    for g in gwasInfo:
        params={'text_list':list(g['trait']),'source':'ukbb'}
        process_res = requests.post('http://vectology-api.mrcieu.ac.uk/preprocess',data=json.dumps(params))
        processed[g]=process_res
    return processed


#text_post()
#orcid_post()
