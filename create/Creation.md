# Building

1. [Get SemMedDB Data](#get-semmeddb-data)
2. [Convert to delimited](#convert-to-delimited) 
3. [Create config.py](#create-config-file) 
4. [Create frequency counts](#create-frequency-counts)
5. [Index the data](#index-the-data)
6. [Create App and API](#create-app-and-api)


### Get SemMedDB Data

Need the SENTENCE, PREDICATION, CITATION and GENERIC_CONCEPT CSV files - https://ii.nlm.nih.gov/SemRep_SemMedDB_SKR/SemMedDB/SemMedDB_download.shtml


### Create config file

`django_project` needs to have config.py file 

```
secret_key=django_secret_key

#elastic host 1 
elastic_host='localhost'
elastic_port='9300'

#path to data storage directory, e.g. where temporary files are stored
dataPath='/path/to/data/'

#Elasticsearch index names
semmed_predicate_index = 'name of predicate index'
semmed_sentence_index = 'name of sentence index'
semmed_triple_freqs_index = 'name predicate frequency index'
semmed_citation_index = 'name of citation index'

semmed_predicate_data = 'location of PREDICATION file, e.g. semmedVER40_R_PREDICATION.csv.gz'
semmed_sentence_data = 'location of SENTENCE data file, e.g. semmedVER40_R_SENTENCE.csv.gz'
semmed_citation_data = 'location of modified CITATION data file, e.g. semmedVER42_2020_R_CITATIONS.csv.gz'
semmed_concept_data = 'location of modified GENERIC_CONCEPT data file, e.g. semmedVER42_2020_R_GENERIC_CONCEPT.csv.gz'
maxPubs=10000000

api_url='api url, e.g. https://www.some.thing/api/'
root_url='root url, e.g. https://www.some.thing/'
debug='True/False'
DEPLOYMENT='dev/prod'

allowed_hosts="allowed hosts"

semmed_triple_total=total number of triples in predicate index
```

### Create frequency counts

`python create/create_semmed_freqs.py`

### Index the data

##### PREDICATION data
 
 - takes ~30 mins

`python create/index_semmeddb_predicate.py`

##### SENTENCE data

 - takes ~5-10 hours

`python create/index_semmeddb_sentences.py`

##### PREDICATION frequency data

- takes 30 mins

`python create/index_semmeddb_freqs.py`

##### CITATION data

- takes ~x hours

`python create/index_semmeddb_citations.py`

### Increase result window and terms count size

```
curl -XPUT 'localhost:9200/semmeddb-v42/_settings' -H 'Content-Type: application/json' -d '{"index.max_result_window" : "1000000"}'
curl -XPUT 'localhost:9200/semmeddb-v42_triple_freqs/_settings' -H 'Content-Type: application/json' -d '{"index.max_result_window" : "1000000"}'
curl -XPUT 'localhost:9200/semmeddb-v42/_settings' -H 'Content-Type: application/json' -d '{"index.max_terms_count" : "100000"}'
curl -XPUT '192.168.0.18:9200/semmeddb-v42_triple_freqs/_settings' -H 'Content-Type: application/json' -d '{"index.max_terms_count" : "100000"}'

```

### Create App and API

To create the App and API just run docker-compose

```
docker-compose up -d
```

# Testing

```
#all
docker exec melodi-presto-django python django_project/manage.py test django_project

#specific
docker exec melodi-presto-django python django_project/manage.py test django_project.tests.APITests
```


