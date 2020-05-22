# Building

1. [Get SemMedDB Data](#get-semmeddb-data)
2. [Convert to delimited](#convert-to-delimited) 
3. [Create config.py](#create-config-file) 
4. [Create frequency counts](#create-frequency-counts)
5. [Index the data](#index-the-data)
6. [Create App and API](#create-app-and-api)


### Get SemMedDB Data

Need the SENTENCE, PREDICATION and CITATION tables - https://ii.nlm.nih.gov/SemRep_SemMedDB_SKR/SemMedDB/SemMedDB_download.shtml

### Convert to delimited 

Downloads are in SQL format, need to convert to something more manageable

```
python create/mysql_to_csv.py <(gunzip -c semmedVER42_2020_R_PREDICATION.sql.gz) | gzip > semmedVER42_2020_R_PREDICATION.tsv.gz
python create/mysql_to_csv.py <(gunzip -c semmedVER42_2020_R_SENTENCE.sql.gz) | gzip > semmedVER42_2020_R_SENTENCE.tsv.gz
python create/mysql_to_csv.py <(gunzip -c semmedVER42_2020_R_CITATIONS.sql.gz) | gzip > semmedVER42_2020_R_CITATIONS.tsv.gz
```

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

semmed_predicate_data = 'location of PREDICATION file, e.g. semmedVER40_R_PREDICATION.psv.gz'
semmed_sentence_data = 'location of SENTENCE data file, e.g. semmedVER40_R_SENTENCE.tsv.gz'
semmed_citation_data = 'location of modified CITATION data file, e.g. semmedVER42_2020_R_CITATIONS.tsv.gz'
maxPubs=10000000

api_url='http://localhost:8000/api/'
debug='True/False'
DEPLOYMENT='dev/prod'

allowed_hosts="allowed hosts"

semmed_triple_total=total number of triples in predicate index
```

### Create frequency counts

`python create/create_semmed_freqs.py`

### Index the data

PREDICATION data

`python create/index-semmeddb_predicate.py`

SENTENCE data

`python create/index-semmeddb-sentences.py`

PREDICATION frequency data

`python create/index-semmeddb_freqs.py`

CITATION data

`python create/index-semmeddb-citations.py`

### Create App and API

To create the App and API just run docker-compose

```
docker-compose up -d
```

# Testing

```
#all
python django_project/manage.py test django_project

#specific
python django_project/manage.py test django_project.tests.APITests
```


