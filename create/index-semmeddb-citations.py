from elasticsearch import Elasticsearch
from elasticsearch import helpers
from collections import deque

import config
import datetime
import time
import gzip

# `SENTENCE_ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
# `PMID` varchar(20) NOT NULL DEFAULT '',
# `TYPE` varchar(2) NOT NULL DEFAULT '',
# `NUMBER` int(10) unsigned NOT NULL DEFAULT '0',
# `SENT_START_INDEX` int(10) unsigned NOT NULL DEFAULT '0',
# `SENT_END_INDEX` int(10) unsigned NOT NULL DEFAULT '0',
# `SECTION_HEADER` varchar(100) DEFAULT NULL,
# `NORMALIZED_SECTION_HEADER` varchar(50) DEFAULT NULL,
# `SENTENCE` varchar(999) CHARACTER SET utf8 NOT NULL DEFAULT '',

es = Elasticsearch([{"host": config.elastic_host, "port": config.elastic_port}],)

timeout = 300


def get_date():
    d = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return d


def create_index(index_name, shards=3):
    print ("Creating index", index_name)
    if es.indices.exists(index_name, request_timeout=timeout):
        print ("Index name already exists, please choose another")
    else:
        print ("Creating index " + index_name)
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


def index_sentence_data(sentence_data, index_name):
    print (get_date(), "Indexing sentence data...")
    create_index(index_name)
    bulk_data = []
    counter = 1
    start = time.time()
    chunkSize = 100000
    with gzip.open(sentence_data) as f:
        # next(f)
        for line in f:
            counter += 1
            if counter % 100000 == 0:
                end = time.time()
                t = round((end - start), 4)
                print (get_date(), sentence_data, t, counter)
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
            l = line.rstrip().decode("utf-8").split("\t")
            if len(l) == 5:
                data_dict = {
                    "PMID": l[0],
                    "ISSN": l[1],
                    "DP": l[2],
                    "EDAT": l[3],
                    "PYEAR": int(l[4]),
                }
                op_dict = {
                    "_index": index_name,
                    "_id": l[0],
                    "_op_type": "create",
                    "_type": "_doc",
                    "_source": data_dict,
                }
                bulk_data.append(op_dict)
            else:
                print('row error',len(l))	
    print(bulk_data[0])
    # print len(bulk_data)
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
    print ("Counting number of records...")
    try:
        es.indices.refresh(index=index_name, request_timeout=timeout)
        res = es.search(index=index_name, request_timeout=timeout)
        esRecords = res["hits"]["total"]
        print ("Number of records in index", index_name, "=", esRecords)
    except timeout:
        print ("counting index timeout", index_name)


index_sentence_data(config.semmed_citation_data, config.semmed_citation_index)
