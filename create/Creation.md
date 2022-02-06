# Building

1. [Get SemMedDB Data](#get-semmeddb-data)
2. [Convert to delimited](#convert-to-delimited) 
3. [Create config.py](#create-config-file) 
4. [Create frequency counts](#create-frequency-counts)
5. [Index the data](#index-the-data)
6. [Create App and API](#create-app-and-api)


### Get SemMedDB Data

Need the SENTENCE, PREDICATION, CITATION and GENERIC_CONCEPT CSV files - https://ii.nlm.nih.gov/SemRep_SemMedDB_SKR/SemMedDB/SemMedDB_download.shtml


### Local virtualenv

Can use this for building and testing local django setup.

```
python3 -m venv venv
. ./venv/bin/activate
pip install -r requirements.txt
```

### Docker 

To create the App and API just run docker-compose

```
docker-compose up -d
```

### Elasticsearch

To create docker instance

```
docker pull docker.elastic.co/elasticsearch/elasticsearch:7.17.0
docker run -p 127.0.0.1:9200:9200 -p 127.0.0.1:9300:9300 -e "discovery.type=single-node" docker.elastic.co/elasticsearch/elasticsearch:7.17.0
```

- the above is for a single node cluster, ideally in production use a full cluster.

### Create config file

Create `django_project/config.py` and modify

```
secret_key = '' # django secret key

#elastic host 
elastic_host = 'localhost' # elasticsearch host
elastic_port = '9200' # elasticsearch port

dataPath = '' # path to data storage directory, e.g. where temporary files are stored

# Elasticsearch index names
semmed_predicate_index = '' # name of predicate index
semmed_sentence_index = '' # name of sentence index
semmed_triple_freqs_index = '' # name predicate frequency index
semmed_citation_index = '' # name of citation index

semmed_predicate_data = '' # location of PREDICATION file, e.g. semmedVER40_R_PREDICATION.csv.gz
semmed_sentence_data = '' # location of SENTENCE data file, e.g. semmedVER40_R_SENTENCE.csv.gz
semmed_citation_data = '' # location of modified CITATION data file, e.g. semmedVER42_2020_R_CITATIONS.csv.gz
semmed_concept_data = '' # location of modified GENERIC_CONCEPT data file, e.g. semmedVER42_2020_R_GENERIC_CONCEPT.csv.gz
maxPubs=10000000

api_url = '' # api url, e.g. http://127.0.0.1:8000/api or https://melodi-presto.mrcieu.ac.uk/api
root_url = '' # root url, e.g. http://127.0.0.1:8000 or https://melodi-presto.mrcieu.ac.uk
debug = 'False' # True/False 
DEPLOYMENT = 'prod' # dev/prod

allowed_hosts = "" # set IP addresses for access

semmed_triple_total = '' # total number of triples in predicate index
```

- create secret key `python -c "import secrets; print(secrets.token_urlsafe())"`


### Create frequency counts

`python -m create.create_semmed_freqs`

### Index the data

##### PREDICATION data
 
 - takes ~30 mins

`python -m create.index_semmeddb_predicate`

##### SENTENCE data

 - takes ~5-10 hours

`python -m create.index_semmeddb_sentences`

##### PREDICATION frequency data

- takes 30 mins

`python -m create.index_semmeddb_freqs`

##### CITATION data

- takes ~x hours

`python -m create.index_semmeddb_citations`

### Increase result window and terms count size

```
curl -XPUT 'localhost:9200/semmeddb-v42/_settings' -H 'Content-Type: application/json' -d '{"index.max_result_window" : "1000000"}'
curl -XPUT 'localhost:9200/semmeddb-v42_triple_freqs/_settings' -H 'Content-Type: application/json' -d '{"index.max_result_window" : "1000000"}'
curl -XPUT 'localhost:9200/semmeddb-v42/_settings' -H 'Content-Type: application/json' -d '{"index.max_terms_count" : "100000"}'
curl -XPUT '192.168.0.18:9200/semmeddb-v42_triple_freqs/_settings' -H 'Content-Type: application/json' -d '{"index.max_terms_count" : "100000"}'

```

# Testing

```
#all
docker exec melodi-presto-django python django_project/manage.py test django_project

#specific
docker exec melodi-presto-django python django_project/manage.py test django_project.tests.APITests
```


