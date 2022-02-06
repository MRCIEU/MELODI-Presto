from elasticsearch import Elasticsearch
import gzip
import config
import csv
import time
import requests
import subprocess
import re
from random import randint


def get_pubmed_info(pmid):
    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        # https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=22368089&retmode=json

        params = {"db": "pubmed", "id": pmid, "retmode": "json"}
        print(url, params)
        r = requests.get(url, params=params).json()
        title = r["result"][pmid]["title"]
        return {"title": title}
    except:
        return {"title": "NA"}


def pubmed_query_to_pmids(query):
    start = time.time()
    print("\n### Getting ids for " + query + " ###")
    url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
    # cap at 1million
    params = {"db": "pubmed", "term": query, "retmax": "1000000", "rettype": "uilist"}
    print(url, params)
    # GET with params in URL
    r = requests.get(url, params=params)

    # create random file name
    n = 10
    ran = "".join(["%s" % randint(0, 9) for num in range(0, n)])

    ranFile = "/tmp/" + ran + ".txt"
    out = open(ranFile, "w")
    out.write(r.text)
    out.close()
    r.status_code
    end = time.time()
    print("Time taken:", round((end - start) / 60, 3), "minutes")

    # count the number of pmids
    cmd = "grep -c '<Id>' " + ranFile
    pCount = 0
    # print(cmd)
    # check for empty searches
    try:
        pCount = int(subprocess.check_output(cmd, shell=True))
    except:
        print("No results")

    print("Total pmids: " + str(pCount))
    counter = 0
    pmidList = []
    if 0 < pCount < config.maxPubs:
        print("\n### Parsing ids ###")
        start = time.time()
        f = open("/tmp/" + ran + ".txt", "r")
        for line in f:
            l = re.search(r".*?<Id>(.*?)</Id>", line)
            if l:
                pmid = l.group(1)
                pmidList.append(pmid)
    elif pCount > config.maxPubs:
        print("too many pmids", config.maxPubs)
    else:
        print("no articles for query", query)
    return pmidList
