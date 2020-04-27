### Sent2Vec models

https://github.com/epfml/sent2vec/issues/49

### Testing

```
#all
python manage.py test django_project

#specific
python manage.py test django_project.tests.OrcidTests
```

##### sent2vec vector for each GWAS trait
```
awk -F "\t" '{print $2}' data/gwas-info-from-api.tsv | xargs -I % curl -X POST "http://textbase.biocompute.org.uk/api/sent2vec-vec/" -H "accept: application/json" -H "Content-Type: application/json" -H "X-CSRFToken: cBVc82HDD3cozeAkO0h5uADxrmxk8jQOfiAdRk9PFCvVRp8K8nhYvriL8rX8p9Bj" -d "{ \"s\": \"%\"}"
``` 
