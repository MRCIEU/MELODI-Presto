# Building

1. [Get SemMedDB Data](#get-semmeddb-data)
2. [Convert to delimited](#convert-to-delimited) 
3. [Create config.py](#create-config-file) 
4. [Create frequency counts](#create-frequency-counts)
5. [Index the data](#index-the-data)
6. [Create App and API](#create-app-and-api)


### Get SemMedDB Data

Need the SENTENCE and PREDICATION tables - https://skr3.nlm.nih.gov/SemMedDB/download/download.html

### Convert to delimited 

Downloads are in SQL format, need to convert to something more manageable

```
python create/mysql_to_csv.py <(gunzip -c semmedVER40_R_PREDICATION.sql.gz) | gzip > semmedVER40_R_PREDICATION.tsv.gz
python create/mysql_to_csv.py <(gunzip -c semmedVER40_R_SENTENCE.sql.gz) | gzip > semmedVER40_R_SENTENCE.tsv.gz
```

### Create config file

`django_project` needs to have config.py file 

```
secret_key=django_secret_key

#elastic host 1 
elastic_host='localhost'
elastic_port='9300'

#elastic host 2
elastic_host_local='localhost'
elastic_port_local='9200'

#path to data storage directory, e.g. where temporary files are stored
dataPath='/path/to/data/'

#Elasticsearch index names
semmed_index = 'name of predicate index'
semmed_sentence_index = 'name of sentence index'
semmed_triple_freqs_index = 'name predicate frequency index '

semmed_predicate_data = 'location of PREDICATION file, e.g. semmedVER40_R_PREDICATION.psv.gz'
semmed_sentence_data = 'location of SENTENCE data file, e.g. semmedVER40_R_SENTENCE.tsv.gz
maxPubs=10000000

api_url='http://localhost:8000/api/'
debug='True/False'
DEPLOYMENT='dev/prod'
```

### Create frequency counts

`python create/create_semmed_freqs.py`

### Index the data

PREDICATION data

`python create/index-semmeddb.py`

SENTENCE data

`python create/index-semmeddb-sentences.py`

PREDICATION frequency data

`python create/index-semmeddb_freqs.py`

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


