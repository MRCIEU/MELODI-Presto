import config
import time
from elasticsearch import Elasticsearch, RequestsHttpConnection, serializer, compat, exceptions, helpers

es = Elasticsearch(
	[{'host': config.elastic_host,'port': config.elastic_port}],
)
es_local = Elasticsearch(
        [{'host': config.elastic_host_local,'port': config.elastic_port_local}],
)
print(es.info())
print(es_local.info())
timeout=300

def make_chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	for i in range(0, len(l), n):
		yield l[i:i + n]

def get_pubmed_data_from_elastic(pmidList=[],doiList=[]):
	#print(doiList,pmidList)
	if not doiList:
		print('Searching medline index only using pmids')
		filterData={"terms":{"pmid":pmidList}}
	elif not pmidList:
		print('Searching medline index only using dois')
		filterData={"terms":{"doi":doiList}}
	else:
		print('Searching medline index using both pmids and dois')
		filterData=[
			{"terms":{"pmid":pmidList}},
			{"terms":{"doi":doiList}}
			]
	start=time.time()
	print('filterData')
	print(filterData)
	res=es_local.search(
		request_timeout=60,
		index='medline',
		body={
			#"profile":True,
			"size":1000000,
			"query": {
				"bool" : {
					"should" : filterData
				}
			}
		})
	end = time.time()
	t=round((end - start), 4)
	print("Time taken:",t, "seconds")
	#print(res['hits']['total'])
	return t,res['hits']['total'],res['hits']['hits']

def check_ngram_es(pmidList):
	print('Checking medline-ngrams for matches to PMIDs:',len(pmidList))
	#print(filterData)
	pmidHits = set()
	chunkSize=1000
	chunkCount=0
	start=time.time()
	pSplit = make_chunks(pmidList,chunkSize)
	for p in pSplit:
		filterData={"terms":{"pmid":p}}
		chunkCount+=1
		res=es_local.search(
			request_timeout=timeout,
			index='medline-ngrams',
			body={
				#"profile":True,
				"size":1000000,
				"_source":["pmid"],
				"query": {
					"bool" : {
						"filter" : filterData
					}
				}
			})
		total = res['hits']['total']
		print(chunkCount,total)
		for r in res['hits']['hits']:
			#print(r['_source'])
			pmidHits.add(r['_source']['pmid'])
		#print(res['hits']['total'])
	print('Found',len(pmidHits))
	end = time.time()
	t=round((end - start), 4)
	print("Time taken:",t, "seconds")
	return list(pmidHits)

def get_summary_ngrams(pmidList):
	print("\n### get_summary_ngrams ###")
	unigramCounts={}
	bigramCounts={}
	trigramCounts={}
	chunkSize=1000
	chunkCount=0
	start=time.time()
	#need to split this up as can be lots of hits
	pSplit = make_chunks(pmidList,chunkSize)
	for p in pSplit:
		chunkCount+=1
		print('chunk size:',len(p))
		filterData={"terms":{"pmid":p}}
		#print(filterData)
		res=es_local.search(
			request_timeout=timeout,
			index='medline-ngrams',
			body={
				"size":1000000,
				"query": {
					"bool" : {
						"filter" : filterData
					}
				}
			})
		total = res['hits']['total']
		print(chunkCount,total)
		for r in res['hits']['hits']:
			#print(res)
			#check for records with no data
			if 'type' in r['_source']:
				ngram_type = r['_source']['type']
				ngram_value = r['_source']['value']
				ngram_count = r['_source']['count']
				if ngram_type=='unigram':
					if ngram_value in unigramCounts:
						unigramCounts[ngram_value]+=ngram_count
					else:
						unigramCounts[ngram_value]=ngram_count
				elif ngram_type=='bigram':
					if ngram_value in bigramCounts:
						bigramCounts[ngram_value]+=ngram_count
					else:
						bigramCounts[ngram_value]=ngram_count
				elif ngram_type=='trigram':
					if ngram_value in trigramCounts:
						trigramCounts[ngram_value]+=ngram_count
					else:
						trigramCounts[ngram_value]=ngram_count
		#print(res['hits']['total'])
	end = time.time()
	t=round((end - start), 4)
	#print(res['hits']['total'])
	print("Time taken:",t, "seconds")
	uSorted = sorted(unigramCounts.items(), key=lambda kv: kv[1],reverse=True)
	bSorted = sorted(bigramCounts.items(), key=lambda kv: kv[1],reverse=True)
	tSorted = sorted(trigramCounts.items(), key=lambda kv: kv[1],reverse=True)
	return uSorted,bSorted,tSorted

def create_medline_ngram_index():
	request_body ={
	    "settings":{
	    "number_of_shards" : 5,
	    "number_of_replicas":1,
	    "index.max_result_window": 1000000
	    },
	    "mappings":{
	        "_doc" : {
	            "properties": {
	                "pmid": { "type": "keyword"},
	                "type": { "type": "keyword"},
	                "value": { "type": "text"},
	                "count": { "type": "long"}
	            }
	        }
	    }
	}
	es.indices.create(index = 'medline-ngrams', body = request_body, request_timeout=timeout)

def add_medline_ngram(pmid,type,data):
	#print('Adding ngrams...')
	ngramData = []
	if data:
		for d in data:
			#print(d)
			value = d['t1']
			if type == 'bigram':
				value = d['t1']+' '+d['t2']
			elif type == 'trigram':
				value = d['t1']+' '+d['t2']+' '+d['t3']
			#deal with /abstracttext
			if '/abstracttext' not in value:
				ngramData.append({'_index': 'medline-ngrams', '_id' : pmid+':'+value, '_type': '_doc', "_op_type": 'index', '_source':
					{"pmid":pmid,
					"type":type,
					"value": value,
					"count": int(d['count'])
					}
					})
	else:
		print('No ngram data!',pmid,type)
		ngramData.append({'_index': 'medline-ngrams', '_type': '_doc', "_op_type": 'index', '_source': {"pmid":pmid}})
	res = helpers.bulk(es, ngramData, raise_on_exception=False, request_timeout=60,chunk_size=1000)


def check_medline_ngram_index():
	if es_local.indices.exists('medline-ngrams', request_timeout=timeout):
		pass
	else:
		print('Creating medline-ngrams index')
		create_medline_ngram_index()

def refresh_index(index_name):
	es.indices.refresh(index_name,request_timeout=timeout)
