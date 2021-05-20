from elasticsearch import Elasticsearch
from elasticsearch import helpers
from collections import deque

import config
import datetime
import time
import gzip
import pandas as pd
from loguru import logger

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
    "clna",
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
                        "OBJECT_CUI": {"type": "keyword"},
                        "OBJECT_NAME": {"type": "keyword"},
                        "OBJECT_SEMTYPE": {"type": "keyword"},
                        "SUB_PRED_OBJ": {"type": "keyword"},
                    }
                }
            },
        }
        es.indices.create(index=index_name, body=request_body, request_timeout=timeout)


def index_predicate_data(predicate_data, concept_data, index_name):
    print(get_date(), "Indexing predicate data...")
    create_index(index_name)
    bulk_data = []
    counter = 1
    start = time.time()
    chunkSize = 100000
    pmids = []

    df = pd.read_csv(predicate_data, encoding="ISO-8859-1")
    col_names = [
        "PREDICATION_ID",
        "SENTENCE_ID",
        "PMID",
        "PREDICATE",
        "SUBJECT_CUI",
        "SUBJECT_NAME",
        "SUBJECT_SEMTYPE",
        "SUBJECT_NOVELTY",
        "OBJECT_CUI",
        "OBJECT_NAME",
        "OBJECT_SEMTYPE",
        "OBJECT_NOVELTY",
        "x",
        "y",
        "z",
    ]
    df.columns = col_names
    logger.info(f"\n{df.head()}")
    logger.info(df.shape)

    # catch bad entries in novelty

    # filter on predicates
    df = df[~df.PREDICATE.isin(predIgnore)]
    logger.info(df.shape)

    # use generic concept file instead of novelty columns
    gc_df = pd.read_csv(concept_data, names=["concept_id", "cui", "name"])
    gc_ids = list(gc_df["cui"])
    logger.info(gc_df.head())
    df = df[~(df["SUBJECT_CUI"].isin(gc_ids)) & ~(df["OBJECT_CUI"].isin(gc_ids))]
    logger.info(f"\n{df.head()}")
    logger.info(df.shape)

    # remove last three cols
    df.drop(columns=["x", "y", "z"], inplace=True)

    for i, row in df.iterrows():
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

        # ignore records with specified types
        pred_id = (
            row["SUBJECT_NAME"] + ":" + row["PREDICATE"] + ":" + row["OBJECT_NAME"]
        )
        pmids.append(row["PMID"])
        # print(l)
        data_dict = {
            "PREDICATION_ID": row["PREDICATION_ID"],
            "SENTENCE_ID": row["SENTENCE_ID"],
            "PMID": row["PMID"],
            "PREDICATE": row["PREDICATE"],
            "SUBJECT_CUI": row["SUBJECT_CUI"],
            "SUBJECT_NAME": row["SUBJECT_NAME"],
            "SUBJECT_SEMTYPE": row["SUBJECT_SEMTYPE"],
            "OBJECT_CUI": row["OBJECT_CUI"],
            "OBJECT_NAME": row["OBJECT_NAME"],
            "OBJECT_SEMTYPE": row["OBJECT_SEMTYPE"],
            "SUB_PRED_OBJ": pred_id,
        }
        op_dict = {
            "_index": index_name,
            "_id": row["PREDICATION_ID"],
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

    # print pmids
    print("Writing pmids...")
    with open("data/pmids.txt", "w") as f:
        for item in list(set(pmids)):
            f.write("%s\n" % item)

    # check number of records, doesn't work very well with low refresh rate
    print("Counting number of records...")
    try:
        es.indices.refresh(index=index_name, request_timeout=timeout)
        res = es.search(index=index_name, request_timeout=timeout)
        esRecords = res["hits"]["total"]
        print("Number of records in index", index_name, "=", esRecords)
    except timeout:
        print("counting index timeout", index_name)


if __name__ == "__main__":
    index_predicate_data(
        config.semmed_predicate_data,
        config.semmed_concept_data,
        config.semmed_predicate_index,
    )
