import requests
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
plt.rcParams["figure.figsize"] = (30,30)

API_URL = "https://melodi-presto.mrcieu.ac.uk/api/"

def enrich(q):
    endpoint = "/enrich/"
    url = f"{API_URL}{endpoint}"
    params = {
        "query": q,
    }
    response = requests.post(url, data=json.dumps(params))
    try:
        res = response.json()
        enrich_df = (
                pd.json_normalize(res)
        )
        return enrich_df
    except:
        print('No data')
        return []

def overlap(q1,q2):
    endpoint = "/overlap/"
    url = f"{API_URL}{endpoint}"
    params = {
        "x": q1,
        "y": q2,
    }
    response = requests.post(url, data=json.dumps(params))
    res = response.json()
    if 'data' in res:
        overlap_df = (    
            pd.json_normalize(res['data'])
        )
    else:
        overlap_df=pd.DataFrame()
    #overlap_df
    return overlap_df


def sentence(q):
    endpoint = "/sentence/"
    url = f"{API_URL}{endpoint}"
    params = {
        "pmid": pmid,
    }
    response = requests.post(url, data=json.dumps(params))
    res = response.json()
    pub_df = (
        pd.json_normalize(res['data'])
    )
    return pub_df    

#identifies overlapping PubMed IDs in an overlap row
def pub_check(row):
    px = set(row['pmids_x'].split(' '))
    py = set(row['pmids_y'].split(' '))
    check=[]
    if len(px.intersection(py)) > 0: 
        return False
    else:
        return True
	
def plot_overlap_counts(overlap_counts):
	#convert to df
	overlap_counts = overlap_counts.reset_index(name='counts')
	#add type to term to avoid duplicate terms with different types
	overlap_counts.object_name_x=overlap_counts.object_name_x+' ('+overlap_counts.object_type_x+')'

	#this just makes it look a bit better
	sns.set(rc={'figure.figsize':(20,20)})

	g = sns.catplot(
		y="object_name_x", 
		x="counts", 
		hue="object_type_x", 
		data=overlap_counts, 
		height=10, 
		kind="bar", 
		palette="muted", 
		orient='horizontal',
		dodge=False,   
		legend=False
	)
	#add numbers to the bars
	for i, v in enumerate(overlap_counts['counts']):
		plt.text(v + 1, i + .25, str(v))
		
	g.set(ylabel='Overlapping term', xlabel='Term frequency')
	plt.legend(title='Term Type',loc='lower right')
	#plt.savefig('overlaps.png',dpi=1000)
	return plt