### Usage

Details on how to use the method can be found [here](Usage.md)

### Creation

Details on how the method was created can be found [here](Creation.md)

### About

Previously we created MELODI, a method and tool to derive overlapping enriched literature elements connecting two biomedical terms, e.g. an exposure and a disease, [(Elsworth et al., 2018)](https://doi.org/10.1093/ije/dyx251). The main data involved were derived from SemMedDB [(Kilicoglu et al., 2012)](https://academic.oup.com/bioinformatics/article/28/23/3158/195282), in particular a set of annotated ‘subject-predicate-object’ triples created from the titles and abstracts of almost 30 million biomedical articles. 

All data were housed in a Neo4j graph, and each query term of interest created connections between the query and the associated literature nodes. This approach provided a suitable method for this type of analysis, and storing the data in a graph made sense, however, creating new links and performing large queries (those that search large parts of the graph and return large amounts of data) was not efficient. In addition, the graph contained all data from the PREDICATION table from SemMedDB, which contains lots of predicates and types that were not informative. 

It was also becoming apparent that limiting searches to two query terms was not ideal. For exaple, cases where a set of genes had been identified with potential links to a disease could not be queried efficiently and the results were impossible to disentangle. There was also a developing need to do many queries, and doing this via the web application was not practical, therefore the development of a programatic method was required.

To address all these issues, we created MELODI Lite. A quicker and more agile method to identify overlapping elements between any number of exposures and outcomes. The modifications made to the data, architecture and method are listed below:

##### Filter by term type

SemMedDB triples were filtered to include only those matching particular ‘term types’. These types are defined by the UMLS semantic type abbreviations (https://mmtx.nlm.nih.gov/MMTx/semanticTypes.shtml). We decided to focus on terms that would be most relevant to mechanistic inference. Table 1 lists the terms that were selected.

Table 1. UMLS semantic types included in MELODI Lite  

```
curl -X GET "localhost:9200/semmeddb-v40/_search?pretty" -H 'Content-Type: application/json' -d'
{
    "aggs" : {
        "sub_type" : {
            "terms" : { "field" : "SUBJECT_SEMTYPE" }
        }
    }
}
```

'
|Type acronym | Type full name	| Subject Count	| Object Count |
|---|---|---|---|
|aapp	|Amino Acid, Peptide, or Protein	|2,796,833	|1,506,909|
|gngm	|Gene or Genome	|1,172,983	|1,957,313|
|orch	|Organic Chemical	|1,106,038	|556,152|
|dsyn	|Disease or Syndrome	|877,924	|2,144,961|
|horm	|Hormone	|235,704	|104,903|
|hops	|Hazardous or Poisonous Substance	|167,979	|99,867|
|inch	|Inorganic Chemical	|134,810	|160,096|
|enzy	|Enzyme	|35,497	|46,044|
|chem	|Chemical	|15,318	|13,156|


##### Filter by predicate type

To improve the usabilty of the data some of the more ambiguous predicates. Table 2 lists the predicates that were included from the data set and their counts.

Table 2. SemMedDB predicate counts

|Predicate	|Count|
|---|---|
|INTERACTS_WITH	|1,380,989|
|COEXISTS_WITH	|1,140,016|
|STIMULATES	|963,361|
|INHIBITS	|811,880|
|ASSOCIATED_WITH	|588,931|
|CAUSES	|440,794|
|PRODUCES	|191,128|
|AFFECTS	|165,378|
|PREDISPOSES	|163,829|
|TREATS	|127,225|


##### Use Elasticsearch instead of Neo4j

As this was now a simpler lookup problem, and not something requiring complex relatioships, Elasticsearch was more selected as the architecture within which to search thedata. Previous experience (https://ieup4.blogs.bristol.ac.uk/2019/04/16/exploring-elasticsearch-architectures-with-oracle-cloud/) had also identified this method as suitably quick for this type of analysis. 
    
##### Enrichment

For enrichment analysis counts of all triples were performed using Elasticsearch aggregation calls and added to a separate index. The enrichment method follows the same principle as MELODI, using a standard 2x2 Fisher’s exct test. For example, if a query ‘Sleep duration’ returned a set of triples "Sleep Apnea, Obstructive:PREDISPOSES:Hypertensive disease" then we can count the number of these triples (a), the number of total triples matched to the query (b), the total number of these triples in the data base (c), and the total number of triples in the database (d).

```
import scipy.stats as stats

a,b,c,d=[10,3505,147,6611441]
oddsratio, pvalue = stats.fisher_exact([[a, b], [c, d]])
oddsratio,pvalue

(128.31894184207206, 3.088447435637683e-18)
```

##### Performance

A first pass creates local copies of the enrichment data, as seen above. For this reason if a variable has not been run already it may take a few moments. However, if an existing variable is queried, the function runs in seconds.

```
time curl -o test.out -X POST 'http://textbase.mrcieu.ac.uk/api/overlap/' -H 'accept: application/json' -H 'Content-Type: application/json' -d '{ "x": [ "Sleep duration" ], "y": [ "Breast cancer" ]}'

real	0m0.367s
user	0m0.010s
sys	0m0.014s
```

