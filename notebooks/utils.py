import requests
import json
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import networkx as nx
import operator 

from networkx.drawing.nx_pydot import graphviz_layout


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

def add_newlines(text):
    text = text.replace(" ", "\n")
    return text

def create_overlap_network(overlap_df):
    
    overlap_df.loc[:, "set_x"] = overlap_df["set_x"].apply(
        lambda x: x.upper()
    )
    overlap_df.loc[:, "set_y"] = overlap_df["set_y"].apply(
        lambda x: x.upper()
    )
    exposure = [add_newlines(x) for x in overlap_df["set_x"].unique()]
    outcome = [add_newlines(x) for x in overlap_df["set_y"].unique()]
    # create network data
    d = []
    d = overlap_df[["set_x", "subject_name_x"]].values.tolist()
    d = d + overlap_df[["object_name_y", "set_y"]].values.tolist()
    d = d + overlap_df[["subject_name_x", "object_name_x"]].values.tolist()
    d = d + overlap_df[["subject_name_y", "object_name_y"]].values.tolist()



    # add newlines to text to make them fit in the nodes! Got to be a better way to do this....
    d_edit = []
    for i in d:
        d_edit.append([add_newlines(x) for x in i])

    # create the edge labels
    labels = {}
    for l in overlap_df[
        ["subject_name_x", "object_name_x", "predicate_x", "localCount_x"]
    ].values.tolist():
        labels[(add_newlines(l[0]), add_newlines(l[1]))] = (
            add_newlines(l[2]) + " (" + str(l[3]) + ")"
        )
    for l in overlap_df[
        ["subject_name_y", "object_name_y", "predicate_y", "localCount_y"]
    ].values.tolist():
        labels[(add_newlines(l[0]), add_newlines(l[1]))] = (
            add_newlines(l[2]) + " (" + str(l[3]) + ")"
        )

    # create the network
    plt.figure(figsize=(15, 15))

    G = nx.Graph(d_edit)

    pos = graphviz_layout(G)

    node_size = 8000

    nx.draw(
        G,
        pos,
        with_labels=True,
        node_size=node_size,
        node_color="skyblue",
        font_size=11,
    )

    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=15)

    # colour the GWAS nodes
    #exposure_outcome_nodes = exposure+outcome
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=exposure,
        node_color="r",
        node_size=node_size,
        alpha=0.5,
    )
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=outcome,
        node_color="g",
        node_size=node_size,
        alpha=0.5,
    )
    
    return plt,G