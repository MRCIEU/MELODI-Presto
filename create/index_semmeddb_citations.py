from elasticsearch import Elasticsearch
from elasticsearch import helpers
from collections import deque
from loguru import logger
import django_project.config as config
import datetime
import time
import gzip
import pandas as pd

# PMID: PubMed identifier of the citation
# ISSN: ISSN identifier of the journal or the proceedings where the article was published
# DP: Publication date for the citation
# EDAT: The date when the citation was added to PubMed
# PYEAR: Completion date for the citation

es = Elasticsearch(
    [{"host": config.elastic_host, "port": config.elastic_port}],
)

timeout = 300


def get_date():
    d = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return d


def create_index(index_name, shards=3):
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
                "index.max_result_window": 1000,
            },
            "mappings": {
                "_doc": {
                    "properties": {
                        "PMID": {"type": "keyword"},
                        "ISSN": {"type": "keyword"},
                        "DP": {"type": "keyword"},
                        "EDAT": {"type": "keyword"},
                        "PYEAR": {"type": "integer"},
                    }
                }
            },
        }
        es.indices.create(index=index_name, body=request_body, request_timeout=timeout)


def read_pmids():
    df = pd.read_csv("data/pmids.txt", header=None, dtype=str, names=["pmid"])
    return df["pmid"].tolist()


def index_sentence_data(sentence_data, index_name):
    print(get_date(), "Indexing sentence data...")
    create_index(index_name)
    bulk_data = []
    counter = 1
    start = time.time()
    chunkSize = 100000
    pmids = set(read_pmids())

    logger.info(f"Reading {sentence_data}")
    df = pd.read_csv(sentence_data)
    col_names = ["PMID", "ISSN", "DP", "EDAT", "PYEAR"]
    df.columns = col_names
    df.fillna("NA", inplace=True)
    logger.info(f"\n{df.head()}")
    logger.info(df.shape)

    for i, row in df.iterrows():
        counter += 1
        if counter % 100000 == 0:
            end = time.time()
            t = round((end - start), 4)
            print(len(bulk_data), get_date(), sentence_data, t, counter)
        if counter % chunkSize == 0:
            deque(
                helpers.streaming_bulk(
                    client=es,
                    actions=bulk_data,
                    chunk_size=chunkSize,
                    request_timeout=timeout,
                    raise_on_error=True,
                ),
                maxlen=0,
            )
            bulk_data = []
        # print(line.decode('utf-8'))
        # PMID = row['PMID'].replace("'", "")
        if str(row["PMID"]) in pmids:
            data_dict = {
                "PMID": row["PMID"],
                "ISSN": row["ISSN"],
                "DP": row["DP"],
                "EDAT": row["EDAT"],
                "PYEAR": int(row["PYEAR"]),
            }

            op_dict = {
                "_index": index_name,
                # "_id": l[0],
                # "_op_type": "create",
                "_type": "_doc",
                "_source": data_dict,
            }
            bulk_data.append(op_dict)
    print(len(bulk_data))
    deque(
        helpers.streaming_bulk(
            client=es,
            actions=bulk_data,
            chunk_size=chunkSize,
            request_timeout=timeout,
            raise_on_error=True,
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


if __name__ == "__main__":
    index_sentence_data(config.semmed_citation_data, config.semmed_citation_index)
