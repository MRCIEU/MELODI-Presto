import config
import time
from elasticsearch import (
    Elasticsearch,
    RequestsHttpConnection,
    serializer,
    compat,
    exceptions,
    helpers,
)

es = Elasticsearch(
    [{"host": config.elastic_host, "port": config.elastic_port}],
)
es_local = Elasticsearch(
    [{"host": config.elastic_host_local, "port": config.elastic_port_local}],
)
print(es.info())
print(es_local.info())
timeout = 300


def make_chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i : i + n]


def get_pubmed_data_from_elastic(pmidList=[], doiList=[]):
    # print(doiList,pmidList)
    if not doiList:
        print("Searching medline index only using pmids")
        filterData = {"terms": {"pmid": pmidList}}
    elif not pmidList:
        print("Searching medline index only using dois")
        filterData = {"terms": {"doi": doiList}}
    else:
        print("Searching medline index using both pmids and dois")
        filterData = [{"terms": {"pmid": pmidList}}, {"terms": {"doi": doiList}}]
    start = time.time()
    print("filterData")
    print(filterData)
    res = es_local.search(
        request_timeout=60,
        index="medline",
        body={
            # "profile":True,
            "size": 1000000,
            "query": {"bool": {"should": filterData}},
        },
    )
    end = time.time()
    t = round((end - start), 4)
    print("Time taken:", t, "seconds")
    # print(res['hits']['total'])
    return t, res["hits"]["total"], res["hits"]["hits"]


def refresh_index(index_name):
    es.indices.refresh(index_name, request_timeout=timeout)
