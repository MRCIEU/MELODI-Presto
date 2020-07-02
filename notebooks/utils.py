import requests
import json
import pandas as pd

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