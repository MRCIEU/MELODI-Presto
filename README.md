# Building

1. [Get SemMedDB Data](#Get SemMedDB Data)
2. Convert to tab delimited 
3. Create frequency counts
4. Index the Predication data
5. Index the Sentence data
6. Index the frequency counts
7. Create config.py 
8. Create App/API



### Get SemMedDB Data

### Convert to tab delimited 

Downloads are in SQL format, need to convert to something more manageable

```
for i in *sql.gz; do echo $i; python django_project/scripts/mysql_to_csv.py <(gunzip -c $i) | gzip > ${i%%.*}.tsv.gz; done 
```

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


