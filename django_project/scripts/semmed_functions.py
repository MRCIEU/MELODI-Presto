from elasticsearch import Elasticsearch
from random import randint
from collections import defaultdict
import scipy.stats as stats
import requests
import time
import re
import subprocess
import config
import gzip
import argparse
import os
import json
import pandas as pd
from scripts.pubmed_functions import pubmed_query_to_pmids


#globals

timeout=300

es = Elasticsearch(
	[{'host': config.elastic_host,'port': config.elastic_port}],
)

textbase_data=os.path.join(config.dataPath,'textbase','data/')

#total number of triples
#curl -XGET 'localhost:9200/semmeddb-v40/_count?pretty'
globalPub=6533824

ignoreTerms=['Patients','Disease','Genes','Proteins','Lipids','Neoplasm','Malignant Neoplasms']

def run_standard_query(filterData,index,size=100000):
    print('run_standard_query')
    #print(index)
    start=time.time()
    res=es.search(
        #ignore_unavailable=True,
    	request_timeout=timeout,
    	index=index,
    	body={
    		"size":size,
    		"query": {
    			"bool" : {
    				"filter" : filterData
    			}
    		}

    	})
    end = time.time()
    t=round((end - start), 4)
    #print(res['hits']['total'])
    return t,res['hits']['total'],res['hits']['hits']

def run_sem_query(filterData,index,size=100000):
    print('run_sem_query')
    #print(index)
    start=time.time()
    res=es.search(
        #ignore_unavailable=True,
    	request_timeout=timeout,
    	index=index,
    	body={
    		"size":size,
    		"query": {
    			"bool" : {
    				"must_not" : [
    					{"terms": {"SUBJECT_NAME": ignoreTerms}},
                        {"terms": {"OBJECT_NAME": ignoreTerms}}
    				],
    				"filter" : filterData
    			}
    		}

    	})
    end = time.time()
    t=round((end - start), 4)
    #print(res['hits']['total'])
    return t,res['hits']['total'],res['hits']['hits']

def get_term_stats(index=config.semmed_triple_freqs_index,query=[]):
	filterData={"terms":{"SUB_PRED_OBJ":query}}
	start=time.time()
	res=es.search(
		request_timeout=timeout,
		index=index,
		body={
			"size":1000000,
			"query": {
				"bool" : {
					"filter" : filterData
				}
			}
		}
	)
	end = time.time()
	t=round((end - start), 4)
	#print("Time taken:",t, "seconds")
	return res['hits']['hits']

def create_sem_es_filter(pmidList):
    #don't need the typeFiterList if used when indexing the data
    typeFilterList = [
        "aapp","enzy","gngm","chem","clnd","dysn","horm","hops","inch","orch"
    ]
    filterOptions = [
			{"terms":{"PMID":pmidList}}
			#{"terms":{"OBJECT_SEMTYPE":typeFilterList}},
			#{"terms":{"SUBJECT_SEMTYPE":typeFilterList}}
			]
    return filterOptions

def sem_es_query(filterData,index,predCounts,resDic):
    #print(filterData)
    t,resCount,res=run_sem_query(filterData,index)
    pMatch=[]
    if resCount>0:
        #print(filterData)
        #print(t,resCount)
        for r in res:
            PMID=r['_source']['PMID']
            #PREDICATION_ID=r['_source']['PREDICATION_ID']
            PREDICATE=r['_source']['PREDICATE']
            OBJECT_NAME=r['_source']['OBJECT_NAME']
            OBJECT_SEMTYPE=r['_source']['OBJECT_SEMTYPE']
            OBJECT_CUI=r['_source']['OBJECT_CUI']
            SUBJECT_NAME=r['_source']['SUBJECT_NAME']
            SUBJECT_SEMTYPE=r['_source']['SUBJECT_SEMTYPE']
            SUBJECT_CUI=r['_source']['SUBJECT_CUI']
            PREDICATION_ID=SUBJECT_NAME+':'+PREDICATE+':'+OBJECT_NAME
            if PREDICATION_ID in resDic:
                resDic[PREDICATION_ID]['pmids'].append(PMID)
            else:
                resDic[PREDICATION_ID]={
                    'subject_name':SUBJECT_NAME,
                    'subject_type':SUBJECT_SEMTYPE,
                    'subject_id':SUBJECT_CUI,
                    'predicate':PREDICATE,
                    'object_name':OBJECT_NAME,
                    'object_type':OBJECT_SEMTYPE,
                    'object_id':OBJECT_CUI,
                    'pmids':[PMID]
                    }
            #print(PMID,PREDICATION_ID)
            if PREDICATION_ID in predCounts:
                predCounts[PREDICATION_ID]+=1
            else:
                predCounts[PREDICATION_ID]=1
    #print(resDic)
    return t,resCount,resDic,predCounts



def fet(localSem,localPub,globalSem,globalPub):
	#print(localSem,localPub,globalSem,globalPub)
	oddsratio, pvalue = stats.fisher_exact([[localSem, localPub], [globalSem, globalPub]])
	#print(oddsratio, pvalue)
	return oddsratio,pvalue

def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

def pub_sem(query,sem_trip_dic):
    #check if already done
    fName=textbase_data+query+'.gz'
    if os.path.exists(fName):
        print(query,'already done')
        start = time.time()
        enrichData=[]
        with gzip.open(fName,'r') as f:
            header=next(f)
            for line in f:
                lineData=line.decode('utf-8').rstrip().split('\t')
                enrichData.append({
                    'query':query,
                    'triple':lineData[0],
                    'subject_name':lineData[1],
                    'subject_type':lineData[2],
                    'subject_id':lineData[3],
                    'predicate':lineData[4],
                    'object_name':lineData[5],
                    'object_type':lineData[6],
                    'object_id':lineData[7],
                    'localCount':lineData[8],
                    'localTotal':lineData[9],
                    'globalCount':lineData[10],
                    'globalTotal':lineData[11],
                    'odds':lineData[12],
                    'pval':lineData[13],
                    'pmids':lineData[14]
                    })
        end = time.time()
        t = "{:.4f}".format(end-start)
        print('Time to read',t)
        return enrichData
    else:
        pmidList = pubmed_query_to_pmids(query.replace('_',' '))
        #print(pmidList)
        pCount=len(pmidList)
        print("Total pmids: ",pCount)
        counter=0
        totalRes=0
        predCounts={}
        resDic={}
        chunkSize=100000
        if 0<pCount<config.maxPubs:
            print("\n### Processing ids ###")
            start = time.time()
            pmidChunks = list(divide_chunks(pmidList, chunkSize))
            for i in range(0,len(pmidChunks)):
                print(i,chunkSize)
                filterOptions = create_sem_es_filter(pmidChunks[i])
                t,resCount,resDic,predCounts=sem_es_query(filterData=filterOptions,index=config.semmed_index,predCounts=predCounts,resDic=resDic)
                totalRes+=resCount

            pc = round((float(counter)/float(pCount))*100)
            print(str(pc)+' % : '+str(counter)+' '+str(len(predCounts)))
            end = time.time()
            print("\tTime taken:", round((end - start) / 60, 3), "minutes")
            print('Total results:',totalRes)
            outFile=query.replace(' ','_')+'.gz'
            o = gzip.open(textbase_data+outFile,'w')
            #print(predCounts)
            t="\t".join(['triple','subject_name','subject_type','subject_id','predicate','object_name','object_type','object_id','localCount','localTotal','globalCount','globalTotal','odds','pval','pmids'])+'\n'
            o.write(t.encode('utf-8'))
            #get global number of publications
            globalSem=es.count(index=config.semmed_index)['count']
            print('globalSem = '+str(globalSem))
            #globalSem=25000000

            #get triple freqs
            tripleFreqs = {}
            print('Geting freqs...',len(predCounts))
            #print(list(predCounts.keys()))
            freq_res = get_term_stats(query=list(predCounts.keys()))
            #print(freq_res)
            for i in freq_res:
                tripleFreqs[i['_source']['SUB_PRED_OBJ']]=i['_source']['frequency']

            print('Doing enrichment...')
            start = time.time()
            counter=0
            enrichData=[]
            for k in sorted(predCounts, key=lambda k: predCounts[k], reverse=True):
                counter+=1
                if counter % chunkSize == 0:
                    pc = round((float(counter)/float(len(predCounts)))*100)
                    print(str(pc)+' % : '+str(counter))
                if predCounts[k]>1:
                    if freq_res:
                        odds,pval=fet(predCounts[k],totalRes,tripleFreqs[k],globalSem)
                        t=k+'\t'+resDic[k]['subject_name']+'\t'+resDic[k]['subject_type']+'\t'+resDic[k]['subject_id']+'\t'+resDic[k]['predicate']+'\t'+resDic[k]['object_name']+'\t'+resDic[k]['object_type']+'\t'+resDic[k]['object_id']+'\t'+str(predCounts[k])+'\t'+str(totalRes)+'\t'+str(tripleFreqs[k])+'\t'+str(globalPub)+'\t'+str(odds)+'\t'+str(pval)+'\t'+" ".join(list(set(resDic[k]['pmids'])))+'\n'
                        o.write(t.encode('utf-8'))
                        enrichData.append({
                            'query':query,
                            'triple':k,
                            'subject_name':resDic[k]['subject_name'],
                            'subject_type':resDic[k]['subject_type'],
                            'subject_id':resDic[k]['subject_id'],
                            'predicate':resDic[k]['predicate'],
                            'object_name':resDic[k]['object_name'],
                            'object_type':resDic[k]['object_type'],
                            'object_id':resDic[k]['object_id'],
                            'localCount':predCounts[k],
                            'localTotal':totalRes,
                            'globalCount':tripleFreqs[k],
                            'globalTotal':globalPub,
                            'odds':odds,
                            'pval':pval,
                            'pmids':" ".join(list(set(resDic[k]['pmids'])))
                            })
                    else:
                        continue
                        #print(k,'has no freq')
            o.close()
            if len(predCounts)>1:
            	pc = round((float(counter)/float(len(predCounts)))*100)
            else:
            	pc=100
            print(str(pc)+' % : '+str(counter))
            end = time.time()
            print("\tTime taken:", round((end - start) / 60, 3), "minutes")
            return enrichData

#use pandas
def compare_sem_df(aList,bList):
    pValCut=1e-5
    print('reading a data from',aList)
    all_a = []
    for a in aList:
        aName = os.path.join(textbase_data,a+'.gz')
        if os.path.exists(aName):
            df = pd.read_csv(aName,sep='\t')
            print(df.shape)
            #remove low pval
            df = df[df['pval']<pValCut]
            print(df.shape)
            df['set']=a
            all_a.append(df)
    if len(all_a)>0:
        aframe = pd.concat(all_a, axis=0, ignore_index=True)
        print(aframe.shape)
    else:
        print('aframe is empty')

    print('reading b data from',bList)
    all_b = []
    for b in bList:
        bName = os.path.join(textbase_data,b+'.gz')
        if os.path.exists(bName):
            df = pd.read_csv(bName,sep='\t')
            #remove low pval
            df = df[df['pval']<pValCut]
            df['set']=b
            all_b.append(df)
    if len(all_b)>0:
        bframe = pd.concat(all_b, axis=0, ignore_index=True)
        print(bframe.shape)
    else:
        print('bframe is empty')

    if len(all_a)>0 and len(all_b)>0:
        print('finding overlaps...')
        overlap = aframe.merge(bframe,left_on='object_name',right_on='subject_name')
        print(overlap.head())
        print(overlap.shape)
        #overlap.to_csv('o.txt',sep='\t')
        return {'count':overlap.shape[0],'data':json.loads(overlap.to_json(orient='records'))}
    else:
        return json.dumps({'error':'no overlaps'})


