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

#check by id
#curl -X GET "localhost:9200/semmeddb-v40_triple_freqs/_search?pretty" -H 'Content-Type: application/json' -d' {"query": {"ids" : {"values" : ["Adiponectin:NEG_COEXISTS_WITH:Insulin"]}}}'

#globals

timeout=300

es = Elasticsearch(
	[{'host': config.elastic_host,'port': config.elastic_port}],
)

es_local = Elasticsearch(
        [{'host': config.elastic_host_local,'port': config.elastic_port_local}],
)

textbase_data=os.path.join(config.dataPath,'textbase','data/')

#total number of publications
#curl -XGET 'localhost:9200/semmeddb/_search?pretty' -H "Content-Type: application/json" -d '{"size":0, "aggs" : {"type_count":{"cardinality" :{ "field" : "PMID" }}}}'
globalPub=6611441

#time python scripts/run.py -m compare -a 'CR1,CCDC6,KAT8' -b 'Alzheimers_disease'

ignoreTerms=['Patients','Disease','Genes','Proteins','Lipids','Neoplasm','Malignant Neoplasms']

def run_standard_query(filterData,index,size=100000):
    print('run_standard_query')
    #print(index)
    start=time.time()
    res=es_local.search(
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
    #don't need the typeFiterList if used when indexin the data
	#typeFilterList = [
	#	"aapp","amas","anab","bacs","biof","bpoc","chem","comd","dsyn","emod","enzy","genf","gngm","hcpp","hops","horm","imft","inch",
	#	"moft","mosq","neop","nnon","nsba","orch","orgf","ortf","patf","rcpt","sbst","socb","tisu","topp","virs","vita"]
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

def sem_es_counts(pmidList,index):
	filterData = [
			{"terms":{"PMID":pmidList}},
			]
	#print(filterData)
	t,resCount,res=run_sem_query(filterData,index)
	tripleDic={}
	subjectDic={}
	objectDic={}
	pMatch=[]
	if resCount>0:
		#print(filterData)
		#print(t,resCount)
		for r in res:
			PMID=r['_source']['PMID']
			pMatch.append(PMID)
			#PREDICATION_ID=r['_source']['PREDICATION_ID']
			PREDICATE=r['_source']['PREDICATE']
			OBJECT_NAME=r['_source']['OBJECT_NAME']
			SUBJECT_NAME=r['_source']['SUBJECT_NAME']
			PREDICATION_ID=SUBJECT_NAME+':'+PREDICATE+':'+OBJECT_NAME
			#resDic[PREDICATION_ID]={'sub':SUBJECT_NAME,'pred':PREDICATE,'obj':OBJECT_NAME}
			#print(PMID,PREDICATION_ID)
			if SUBJECT_NAME in subjectDic:
				subjectDic[SUBJECT_NAME]+=1
			else:
				subjectDic[SUBJECT_NAME]=1

			if OBJECT_NAME in objectDic:
				objectDic[OBJECT_NAME]+=1
			else:
				objectDic[OBJECT_NAME]=1

			if PREDICATION_ID in tripleDic:
				tripleDic[PREDICATION_ID]+=1
			else:
				tripleDic[PREDICATION_ID]=1
	#find missing - there are loads of PMIDS not in the raw predicate file, e.g. 15252980, not sure why
	missing=set(pmidList).difference(pMatch)
	subjectDic=sorted(subjectDic.items(), key=lambda kv: kv[1],reverse=True)
	objectDic=sorted(objectDic.items(), key=lambda kv: kv[1],reverse=True)
	tripleDic=sorted(tripleDic.items(), key=lambda kv: kv[1],reverse=True)
	return missing,t,resCount,subjectDic,objectDic,tripleDic

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

def read_sem_triples():
	print('getting background freqs...')
	sem_trip_dic={}
	start = time.time()
	with gzip.open(textbase_data+'semmeddb_triple_freqs.txt.gz') as f:
		for line in f:
			s,f = line.rstrip().split('\t')
			sem_trip_dic[s]=f
	print(len(sem_trip_dic))
	end = time.time()
	print("\tTime taken:", round((end - start) / 60, 3), "minutes")
	return sem_trip_dic

def compare_sem(aList,bList):
    pValCut=1e-5
    predIgnore = ['PART_OF','ISA','LOCATION_OF','PROCESS_OF','ADMINISTERED_TO','METHOD_OF','USES','COEXISTS_WITH','ASSOCIATED_WITH','compared_with']

    aDic=defaultdict(dict)
    print('Reading',aList)
    for a in aList:
    	print(a)
    	with gzip.open(os.path.join(textbase_data,a+'.gz')) as f:
    		for line in f:
    			s,sub_name,sub_type,sub_id,pred,obj_name,obj_type,obj_id,f1,f2,f3,f4,o,p = line.decode('utf-8').rstrip().split('\t')
    			if float(p)<pValCut:
    				if pred not in predIgnore:
    					aDic[a][s]={'subject_name':sub_name,'subject_type':sub_type,'subject_id':sub_id,'object_name':obj_name,'object_type':obj_type,'object_id':obj_id,'predicate':pred,'localCounts':f1,'localTotal':f2,'globalCounts':f3,'globalTotal':f4,'odds':o,'pval':p}
    bDic=defaultdict(dict)
    print('Reading',bList)
    for b in bList:
    	print(b)
    	with gzip.open(os.path.join(textbase_data,b+'.gz')) as f:
    		for line in f:
    			s,sub,pred,obj,f1,f2,f3,f4,o,p = line.decode('utf-8').rstrip().split('\t')
    			if float(p)<pValCut:
    				#ignore less useful predicates
    				if pred not in predIgnore:
    					bDic[b][s]={'subject_name':sub_name,'subject_type':sub_type,'subject_id':sub_id,'object_name':obj_name,'object_type':obj_type,'object_id':obj_id,'predicate':pred,'localCounts':f1,'localTotal':f2,'globalCounts':f3,'globalTotal':f4,'odds':o,'pval':p}
    print(len(aDic))
    print(len(bDic))


    #compare two sets of data
    aComDic=defaultdict(dict)
    bComDic=defaultdict(dict)
    joinDic={}
    predDic={}
    joinCount=0

    #this is inefficient, looping through both dictionaries is not necessary

    for a in aDic:
    	print(a)
    	counter=0
    	for s1 in aDic[a]:
    		counter+=1
    		pc = round((float(counter)/float(len(aDic[a])))*100,1)
    		#print(counter,pc,pc%10)
    		if pc % 10 == 0:
    			print(pc,'%')
    		aSub,aPred,aObj,aPval = aDic[a][s1]['subject_name'],aDic[a][s1]['pred'],aDic[a][s1]['object_name'],aDic[a][s1]['pval']
    		for b in bDic:
    			#print(b)
    			for s2 in bDic[b]:
    				#print(s1,s2)
    				bSub,bPred,bObj,bPval = bDic[b][s2]['subject_name'],bDic[b][s2]['pred'],bDic[b][s2]['object_name'],bDic[b][s2]['pval']
    				#print(aObj,bSub)
    				#testing
    				if bSub in ignoreTerms:
    					continue
    				if aObj == bSub:
                        #this just creates counts of predicates
    					if aPred in predDic:
    						predDic[aPred]+=1
    					else:
    						predDic[aPred]=1
    					if bPred in predDic:
    						predDic[bPred]+=1
    					else:
    						predDic[bPred]=1
    					#print(a,s1,aDic[a][s1],b,s2,bDic[b][s2])
    					aComDic[a][s1]=aDic[a][s1]
    					bComDic[b][s2]=bDic[b][s2]
    					joinCount+=1
    					joinDic[joinCount]={'s1':s1,'s2':s2,'overlap':aObj,'d1':a,'d2':b,'pval1':aPval,'pval2':bPval}
    #get some summaries
    #print(predDic)
    #for c in aComDic:
    #	print(c,len(aComDic[c]))

    #with open(textbase_data+'compare/a_nodes.json','w') as outfile:
    	#outfile={'source':a:'sem':s1:aDic[a][s1]}
    #	json.dump(aComDic,outfile)

    #with open(textbase_data+'compare/b_nodes.json','w') as outfile:
    	#outfile={'source':a:'sem':s1:aDic[a][s1]}
    #	json.dump(bComDic,outfile)

    #o = open(textbase_data+'compare/rels.tsv','w')
    #for i in joinDic:
    #outfile={'source':a:'sem':s1:aDic[a][s1]}
    #	o.write(
    #        str(i)+'\t'+
    #        joinDic[i]['s1']+'\t'+
    #        joinDic[i]['s2']+'\t'+
    #        joinDic[i]['overlap']+'\t'+
    #        joinDic[i]['d1']+'\t'+
    #        joinDic[i]['d2']+'\n')
    #o.close()

    res={}
    res['count']=len(joinDic)
    res['overlaps']=joinDic

    return res

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

if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='SemMedDB enrichment search')
	#parser.add_argument('integers', metavar='N', type=int, nargs='+',
	#                   help='an integer for the accumulator')
	parser.add_argument('-m,--method', dest='method', help='(get_data, compare)')
	parser.add_argument('-q,--query', dest='query', help='the pubmed query')
	parser.add_argument('-a,--query_a', dest='query_a', help='list of enriched data sets')
	parser.add_argument('-b,--query_b', dest='query_b', help='list of enriched data sets')

	args = parser.parse_args()
	print(args)
	if args.method == None:
		print("Please provide a method (-m): [get_data, compare]")
	else:
		if args.method == 'get_data':
			if args.query == None:
				print('Please provide a query (-q) [e.g. pcsk9]')
			else:
				#sem_trip_dic=read_sem_triples()
				sem_trip_dic={}
				print('creating enriched article set')
				queries=args.query.rstrip().split(',')
				for q in queries:
					pub_sem(q,sem_trip_dic)
		elif args.method == 'compare':
			if args.query_a == None or args.query_b == None:
				print('Please provide two lists of data sets to compare (-a and -b)')
			else:
				print('Comparing data...')
				compare_sem(args.query_a,args.query_b)
				#delete_index(args.index_name)
		else:
			print("Not a good method")

#pub_sem('pcsk9')
#pub_sem('oropharyngeal cancer')
#pub_sem('prostate cancer')
#pub_sem('breast cancer')
#get_term_stats('semmeddb_triple_freqs',filterData={"terms":{"SUB_PRED_OBJ":['Encounter due to counseling:PROCESS_OF:Family']}})
