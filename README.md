### API and App

[https://melodi-presto.mrcieu.ac.uk/](https://melodi-presto.mrcieu.ac.uk/)

[![DOI](https://zenodo.org/badge/259267887.svg)](https://zenodo.org/badge/latestdoi/259267887)

### Usage

Details on how to use the method can be found [here](Usage.md)

### Creation

Details on how the method was created can be found [here](create/Creation.md)

### About

Previously we created MELODI, a method and tool to derive overlapping enriched literature elements connecting two biomedical terms, e.g. an exposure and a disease, [(Elsworth et al., 2018)](https://doi.org/10.1093/ije/dyx251). The main data involved were derived from SemMedDB [(Kilicoglu et al., 2012)](https://academic.oup.com/bioinformatics/article/28/23/3158/195282), in particular a set of annotated ‘subject-predicate-object’ triples created from the titles and abstracts of almost 30 million biomedical articles. 

All data were housed in a Neo4j graph, and each query term of interest created connections between the query and the associated literature nodes. This approach provided a suitable method for this type of analysis, and storing the data in a graph made sense, however, creating new links and performing large queries (those that search large parts of the graph and return large amounts of data) was not efficient. In addition, the graph contained all data from the PREDICATION table from SemMedDB, which contains lots of predicates and types that were not informative. 

It was also becoming apparent that limiting searches to two query terms was not ideal. For example, cases where a set of genes had been identified with potential links to a disease could not be queried efficiently and the results were impossible to disentangle. There was also a developing need to do many queries, and doing this via the web application was not practical, therefore the development of a programmatic method was required.

To address all these issues, we created MELODI Presto. A quicker and more agile method to identify overlapping elements between any number of exposures and outcomes. The modifications made to the data, architecture and method are listed below:

##### Filter by term type

SemMedDB triples were filtered to include only those matching particular ‘term types’. These types are defined by the UMLS semantic type abbreviations (https://mmtx.nlm.nih.gov/MMTx/semanticTypes.shtml). We decided to focus on terms that would be most relevant to mechanistic inference. Table 1 lists the terms that were selected.

Table 1. UMLS semantic types included in MELODI Presto 

```
curl -X GET "localhost:9200/semmeddb-v40/_search?pretty" -H 'Content-Type: application/json' -d'
{
    "aggs" : {
        "sub_type" : {
            "terms" : { 
                "field" : "SUBJECT_SEMTYPE" ,
                "size" : 10000
                }
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

To improve the usabilty of the data some of the more ambiguous predicates. Table 2 lists the predicates that were excluded from the data set.

```
zless semmedVER40_R_PREDICATION.tsv.gz | cut -f 4 | sort | uniq -c | sort -nr
```

Table 2. Exluded SemMedDB predicates and their frequency counts

|Predicate	|Count|
|---|---|
| PROCESS_OF | 19,628,964 |
| LOCATION_OF |	16,647,580 |
| PART_OF |	9,920,521 |
| ISA |	5,886,751 |
| USES |	4,487,945 |
| compared_with |	1,056,642 |
| ADMINISTERED_TO	| 1,535,833 |
| METHOD_OF	| 581,303 |

Combined, these two criteria reduce the number of PREDICATE triples from 97,972,561 to 6,533,824.

```
curl -XGET 'localhost:9200/semmeddb-v40/_count?pretty'
{
  "count" : 6533824,
  "_shards" : {
    "total" : 3,
    "successful" : 3,
    "skipped" : 0,
    "failed" : 0
  }
}
```


##### Use Elasticsearch instead of Neo4j

As this was now a simpler lookup problem, and not something requiring complex relatioships, Elasticsearch was more selected as the architecture within which to search thedata. Previous experience (https://ieup4.blogs.bristol.ac.uk/2019/04/16/exploring-elasticsearch-architectures-with-oracle-cloud/) had also identified this method as suitably quick for this type of analysis. 
    
##### Enrichment

For enrichment analysis counts of all triples were performed using Elasticsearch aggregation calls and added to a separate index. The enrichment method follows the same principle as MELODI, using a standard 2x2 Fisher’s exct test. For example, if a query ‘Sleep duration’ returned a set of triples "Sleep Apnea, Obstructive:PREDISPOSES:Hypertensive disease" then we can count the number of these triples (a), the number of total triples matched to the query (b), the total number of these triples in the data base (c), and the total number of triples in the database (d).

```
import scipy.stats as stats

a,b,c,d=[10,3505,147,6611441]
oddsratio, pvalue = stats.fisher_exact([[a, b-a], [c, d-c]])
oddsratio,pvalue

(128.68323065993206, 3.002903135377263e-18)
```

##### Performance

A first pass creates local copies of the enrichment data, as seen above. For this reason if a variable has not been run already it may take a few moments. However, if an existing variable is queried, the function runs in seconds.

```
q="physical activity"

#first time

time curl -o "physical-activity.melodi-presto.json" -X POST "https://melodi-presto.mrcieu.ac.uk/api/enrich/" -H "accept: application/json" -H "Content-Type: application/json" -d "{ \"query\": [ \"$q\" ]}"

real	0m23.901s
user	0m0.042s
sys	0m0.126s

#second time 

time curl -o "physical-activity.melodi-presto.json" -X POST "https://melodi-presto.mrcieu.ac.uk/api/enrich/" -H "accept: application/json" -H "Content-Type: application/json" -d "{ \"query\": [ \"$q\" ]}"

real	0m2.150s
user	0m0.036s
sys	0m0.104s
```

### Notes

The call to PubMed is limited to 1 million articles. 

```
http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi? {'db': 'pubmed', 'term': '', 'retmax': '1000000', 'rettype': 'uilist'}
```
