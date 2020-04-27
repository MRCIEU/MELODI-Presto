# Building

1. [Get SemMedDB Data](#get-semmeddb-data)
2. [Convert to delimited](#convert-to-delimited) 
3. [Create config.py] 
4. [Create frequency counts]
5. [Index the Predication data]
6. [Index the Sentence data]
7. [Index the frequency counts]
8. [Create App/API]



### Get SemMedDB Data

### Convert to delimited 

Downloads are in SQL format, need to convert to something more manageable

```
for i in *sql.gz; do echo $i; python django_project/scripts/mysql_to_csv.py <(gunzip -c $i) | gzip > ${i%%.*}.tsv.gz; done 
```

### Create config.py 

`django_project` needs to have config.py file 

```
secret_key=django_secret_key

#elastic host 1 
elastic_host='localhost'
elastic_port='9300'

#elastic host 2
elastic_host_local='localhost'
elastic_port_local='9200'

#path to data
dataPath='/Users/be15516/projects/textBase/api/django_project/data/'
localPath='/Users/be15516/projects/textBase/api/django_project/data/'
#dataPath='/usr/src/app/django_project/data/'
semmed_index = 'semmeddb-v40'
semmed_triple_freqs = 'semmeddb-v40_triple_freqs'
semmed_data = '/Users/be15516/mounts/rdfs_mrc/research/data/nih/metadata/dev/release_candidate/data/SemMedDB/semmedVER40_R/semmedVER40_R_PREDICATION.psv.gz'
semmed_sentence_index = 'semmeddb-sentence-v40'
maxPubs=10000000

api_url='http://localhost:8000/api/'
debug='True'
DEPLOYMENT='dev'

```

### Create frequency counts

`python django_project/scripts/

### Index the Predication data
### Index the Sentence data
### Index the frequency counts

### Create App/API

To create the App and API just run docker-compose

```
docker-compose up -d
```

# Testing

```
#all
python manage.py test django_project

#specific
python manage.py test django_project.tests.OverlapTests
```


