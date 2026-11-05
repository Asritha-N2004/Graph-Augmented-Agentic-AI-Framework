import json
from collections import Counter
import networkx as nx
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from backend.app.config import ARTIFACTS
from backend.ml.data import FEATURES

def build(c,p,t,f):
    """All behavioral features/edges must originate in the training time window."""
    g=nx.Graph(); ids=list(c.customer_id)+list(p.product_id)+['CAT_'+v for v in sorted(p.category.unique())]
    mapping={key:i for i,key in enumerate(ids)}
    clusters=sorted(f.cluster.unique()) if 'cluster' in f else []
    x=np.zeros((len(ids),len(FEATURES)+len(p.category.unique())+len(clusters)+3),dtype=np.float32)
    fc=f.set_index('customer_id').reindex(c.customer_id)
    x[:len(c),:len(FEATURES)]=StandardScaler().fit_transform(np.log1p(fc[FEATURES].clip(lower=0)))
    cats={v:i for i,v in enumerate(sorted(p.category.unique()))}
    preferences=t.merge(p[['product_id','category']],on='product_id').groupby(['customer_id','category']).quantity.sum().unstack(fill_value=0)
    for cu,row in preferences.iterrows():
        for category,value in row.items(): x[mapping[cu],len(FEATURES)+cats[category]]=value/max(row.sum(),1)
    if clusters:
        for row in f.itertuples(): x[mapping[row.customer_id],len(FEATURES)+len(cats)+clusters.index(row.cluster)]=1
    for customer in c.customer_id: g.add_node(customer,type='customer')
    pop=t.groupby('product_id').quantity.sum()
    for row in p.itertuples():
        idx=mapping[row.product_id]; x[idx,len(FEATURES)+cats[row.category]]=1; x[idx,-3:]=[np.log1p(row.price),np.log1p(pop.get(row.product_id,0)),1]
        g.add_node(row.product_id,type='product',name=row.product_name); g.add_node('CAT_'+row.category,type='category'); g.add_edge(row.product_id,'CAT_'+row.category,relation='belongs_to')
    for cat,idx in cats.items(): x[mapping['CAT_'+cat],len(FEATURES)+idx]=1
    for (cu,pr),z in t.groupby(['customer_id','product_id']):
        g.add_edge(cu,pr,relation='purchased_and_interacted',quantity=int(z.quantity.sum()),frequency=int(z.transaction_id.nunique()),spending=float(z.total_amount.sum()),strength=float(np.log1p(z.quantity.sum())),recency=int((t.transaction_date.max()-z.transaction_date.max()).days))
    pairs=Counter()
    for _,z in t.groupby('transaction_id'):
        products=sorted(z.product_id.unique())
        for i,a in enumerate(products):
            for b in products[i+1:]: pairs[(a,b)]+=1
    for (a,b),n in pairs.items(): g.add_edge(a,b,relation='co_purchased',weight=n)
    nn=NearestNeighbors(n_neighbors=4).fit(x[:len(c)])
    for i,neighbors in enumerate(nn.kneighbors(x[:len(c)],return_distance=False)):
        for j in neighbors[1:]: g.add_edge(ids[i],ids[j],relation='similar_customer')
    edges=np.array([(mapping[a],mapping[b]) for a,b in g.edges],dtype=np.int64).T
    edge_index=torch.tensor(np.concatenate([edges,edges[::-1]],axis=1),dtype=torch.long)
    nx.write_graphml(g,ARTIFACTS/'graph/customer_product_graph.graphml'); torch.save(torch.tensor(x),ARTIFACTS/'graph/node_features.pt'); torch.save(edge_index,ARTIFACTS/'graph/edge_index.pt'); (ARTIFACTS/'graph/node_mapping.json').write_text(json.dumps(mapping))
    return g,torch.tensor(x),edge_index,mapping
