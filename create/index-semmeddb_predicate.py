from elasticsearch import Elasticsearch
from elasticsearch import helpers
from collections import deque

import config
import datetime
import time
import gzip

# PREDICATION_ID: Auto-generated primary key for each unique predication
# SENTENCE_ID: Foreign key to the SENTENCE table
# PMID: The PubMed identifier of the citation to which the predication belongs
# PREDICATE: The string representation of each predicate (for example TREATS, PROCESS_OF)
# SUBJECT_CUI: The CUI of the subject of the predication
# SUBJECT_NAME: The preferred name of the subject of the predication
# SUBJECT_SEMTYPE: The semantic type of the subject of the predication
# SUBJECT_NOVELTY: The novelty of the subject of the predication
# OBJECT_CUI: The CUI of the object of the predication
# OBJECT_NAME: The preferred name of the object of the predication
# OBJECT_SEMTYPE: The semantic type of the object of the predication
# OBJECT_NOVELTY: The novelty of the object of the predication

es = Elasticsearch([{"host": config.elastic_host, "port": config.elastic_port}],)

predIgnore = [
    "PART_OF",
    "ISA",
    "LOCATION_OF",
    "PROCESS_OF",
    "ADMINISTERED_TO",
    "METHOD_OF",
    "USES",
    "compared_with",
]
typeFilterList = [
    "aapp",
    "chem",
    "clna"
    "clnd",
    "dsyn",
    "enzy",
    "gngm",
    "horm",
    "hops",
    "inch",
    "orch",
    "phsu",
]

timeout = 300


def get_date():
    d = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return d


def create_index(index_name, shards=5):
    print("Creating index", index_name)
    if es.indices.exists(index_name, request_timeout=timeout):
        print("Index name already exists, please choose another")
    else:
        print("Creating index " + index_name)
        request_body = {
            "settings": {
                "number_of_shards": shards,
                "number_of_replicas": 1,
                # "index.codec": "best_compression",
                "refresh_interval": -1,
                "index.max_result_window": 1000000,
            },
            "mappings": {
                "_doc": {
                    "properties": {
                        "PREDICATION_ID": {"type": "keyword"},
                        "SENTENCE_ID": {"type": "keyword"},
                        "PMID": {"type": "keyword"},
                        "PREDICATE": {"type": "keyword"},
                        "SUBJECT_CUI": {"type": "keyword"},
                        "SUBJECT_NAME": {"type": "keyword"},
                        "SUBJECT_SEMTYPE": {"type": "keyword"},
                        "SUBJECT_NOVELTY": {"type": "integer"},
                        "OBJECT_CUI": {"type": "keyword"},
                        "OBJECT_NAME": {"type": "keyword"},
                        "OBJECT_SEMTYPE": {"type": "keyword"},
                        "OBJECT_NOVELTY": {"type": "integer"},
                        "SUB_PRED_OBJ": {"type": "keyword"},
                    }
                }
            },
        }
        es.indices.create(index=index_name, body=request_body, request_timeout=timeout)


def index_predicate_data(predicate_data, index_name):
    print(get_date(), "Indexing predicate data...")
    create_index(index_name)
    bulk_data = []
    counter = 1
    start = time.time()
    chunkSize = 100000
    with gzip.open(predicate_data) as f:
        # next(f)
        for line in f:
            counter += 1
            if counter % 100000 == 0:
                end = time.time()
                t = round((end - start), 4)
                print(get_date(), predicate_data, t, counter)
            if counter % chunkSize == 0:
                deque(
                    helpers.streaming_bulk(
                        client=es,
                        actions=bulk_data,
                        chunk_size=chunkSize,
                        request_timeout=timeout,
                        raise_on_error=False,
                    ),
                    maxlen=0,
                )
                bulk_data = []
            # print(line.decode('utf-8'))
            l = line.rstrip().decode("utf-8").split("\t")
            # ignore records with specified predicates
            if l[3] in predIgnore:
                continue
            # ignore records with specified types
            if l[6] in typeFilterList and l[10] in typeFilterList:
                pred_id = l[5] + ":" + l[3] + ":" + l[9]
                # print(l)
                data_dict = {
                    "PREDICATION_ID": l[0],
                    "SENTENCE_ID": l[1],
                    "PMID": l[2],
                    "PREDICATE": l[3],
                    "SUBJECT_CUI": l[4],
                    "SUBJECT_NAME": l[5],
                    "SUBJECT_SEMTYPE": l[6],
                    "SUBJECT_NOVELTY": int(l[7]),
                    "OBJECT_CUI": l[8],
                    "OBJECT_NAME": l[9],
                    "OBJECT_SEMTYPE": l[10],
                    "OBJECT_NOVELTY": int(l[11]),
                    "SUB_PRED_OBJ": pred_id,
                }
                op_dict = {
                    "_index": index_name,
                    "_id": l[0],
                    "_op_type": "create",
                    "_type": "_doc",
                    "_source": data_dict,
                }
                bulk_data.append(op_dict)
    # print bulk_data[0]
    # print len(bulk_data)
    deque(
        helpers.streaming_bulk(
            client=es,
            actions=bulk_data,
            chunk_size=chunkSize,
            request_timeout=timeout,
            raise_on_error=False,
        ),
        maxlen=0,
    )

    # check number of records, doesn't work very well with low refresh rate
    print("Counting number of records...")
    try:
        es.indices.refresh(index=index_name, request_timeout=timeout)
        res = es.search(index=index_name, request_timeout=timeout)
        esRecords = res["hits"]["total"]
        print("Number of records in index", index_name, "=", esRecords)
    except timeout:
        print("counting index timeout", index_name)


index_predicate_data(config.semmed_predicate_data, config.semmed_predicate_index)
