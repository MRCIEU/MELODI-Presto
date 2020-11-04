from elasticsearch import Elasticsearch
from elasticsearch import helpers
from collections import deque

import config
import datetime
import time
import gzip
import requests
import os

# could be over 17 million of these
batch_size = 100000
index_name = config.semmed_predicate_index

url = (
    "http://"
    + config.elastic_host
    + ":"
    + config.elastic_port
    + "/"
    + index_name
    + "/_search/"
)
headers = {"Content-Type": "application/json"}

# initial query
# curl -X GET "localhost:9200/semmeddb/_search?pretty" -H 'Content-Type: application/json' -d '{ "aggs" : { "my_buckets" : { "composite": { "size":100, "sources": [{"sub-pred-obj":{"terms" : { "field" : "SUB_PRED_OBJ"}}} ] }}}} '

# after query
# curl -X GET "localhost:9200/semmeddb/_search?pretty" -H 'Content-Type: application/json' -d '{ "aggs" : { "my_buckets" : { "composite": { "size":100, "sources": [{"sub-pred-obj":{"terms" : { "field" : "SUB_PRED_OBJ"}}} ],"after":{"sub-pred-obj":"\"\"\"U\"\" lymphocyte\":LOCATION_OF:receptor"} }}}} '

# check
# curl -XGET 'localhost:9200/semmeddb/_search?pretty' -H 'Content-Type: application/json' -d '{"size":1,"query":{"bool":{"filter":[{"term":{"SUB_PRED_OBJ":"Encounter due to counseling:PROCESS_OF:Family"}}]}}}';

# make output directory
outDir = "data/freqs/" + index_name
if not os.path.exists(outDir):
    os.makedirs(outDir)


def create_counts(type):
    print("Creating counts for ", type)
    if type == "semmeddb_triple":
        source = "SUB_PRED_OBJ"
    elif type == "semmeddb_subject":
        source = "SUBJECT_NAME"
    elif type == "semmeddb_object":
        source = "OBJECT_NAME"
    else:
        print("unkown type!")
        exit()

    # get initial aggreation
    print("Running initial aggregation", source)
    payload = {
        "aggs": {
            "my_buckets": {
                "composite": {
                    "size": batch_size,
                    "sources": [{type: {"terms": {"field": source}}}],
                }
            }
        }
    }

    r = requests.post(url, json=payload, headers=headers)
    res = r.json()
    print(res)
    masterDic = {}
    for r in res["aggregations"]["my_buckets"]["buckets"]:
        val = r["key"][type]
        count = r["doc_count"]
        masterDic[val] = count
    last_entry = res["aggregations"]["my_buckets"]["buckets"][-1]["key"][type]
    # print('last - ',last_entry)

    pageCount = 0
    while True:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(now, pageCount, len(masterDic))
        payload = {
            "aggs": {
                "my_buckets": {
                    "composite": {
                        "size": batch_size,
                        "sources": [{type: {"terms": {"field": source}}}],
                        "after": {type: last_entry},
                    }
                }
            }
        }
        r = requests.post(url, json=payload, headers=headers)
        res = r.json()
        for r in res["aggregations"]["my_buckets"]["buckets"]:
            # print(r['key'])
            val = r["key"][type]
            count = r["doc_count"]
            if val in masterDic:
                print(val, "already exists")
                break
            masterDic[val] = count
        if len(res["aggregations"]["my_buckets"]["buckets"]) > 1:
            last_entry = res["aggregations"]["my_buckets"]["buckets"][-1]["key"][type]
            # print('last - ',last_entry)
            pageCount += 1
        else:
            print("Done")
            break

    print(len(masterDic))
    print("Writing to file...")
    o = gzip.open(outDir + "/" + type + "_freqs.txt.gz", "w")
    for m in masterDic:
        t = m + "\t" + str(masterDic[m]) + "\n"
        o.write(t.encode("utf-8"))


create_counts("semmeddb_triple")
# create_counts('semmeddb_subject')
# create_counts('semmeddb_object')
