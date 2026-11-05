import json
from functools import lru_cache
import joblib
import networkx as nx
import pandas as pd
from backend.app.config import DATA,ARTIFACTS
from backend.ml.recommendation import HybridRecommender

def records(df): return json.loads(df.to_json(orient='records',date_format='iso'))

class Store:
    def __init__(self):
        self.c=pd.read_csv(DATA/'cleaned_customers.csv'); self.p=pd.read_csv(DATA/'products.csv'); self.t=pd.read_csv(DATA/'cleaned_transactions.csv',parse_dates=['transaction_date']); self.f=pd.read_csv(DATA/'processed_customer_features.csv'); self.s=pd.read_csv(ARTIFACTS/'models/customer_segments.csv'); self.summary=pd.read_csv(ARTIFACTS/'models/cluster_summary.csv'); self.rec=HybridRecommender.load_serving(ARTIFACTS/'models',self.p) if (ARTIFACTS/'models/recommendation_state.npz').exists() else joblib.load(ARTIFACTS/'models/recommendation_model.pkl'); self.g=nx.read_graphml(ARTIFACTS/'graph/customer_product_graph.graphml'); self.manifest=json.loads((ARTIFACTS/'models/manifest.json').read_text())
    def metrics(self,name): return json.loads((ARTIFACTS/f'metrics/{name}_metrics.json').read_text())
    def overview(self):
        baskets=self.t.transaction_id.nunique()
        return {'customers':len(self.c),'products':len(self.p),'transactions':int(baskets),'transaction_lines':len(self.t),'revenue':float(self.t.total_amount.sum()),'average_order_value':float(self.t.total_amount.sum()/baskets),'segments':int(self.s.cluster.nunique()),'recommendations':len(self.c)*5,'currency':'INR','data_source':'Synthetic · seed 42','model_version':self.manifest['version'],'training_cutoff':self.manifest['train_end']}
    def revenue(self):
        z=self.t.groupby(self.t.transaction_date.dt.strftime('%Y-%m')).agg(revenue=('total_amount','sum'),transactions=('transaction_id','nunique')).reset_index().rename(columns={'transaction_date':'month'}); return records(z)
    def products(self): return records(self.t.merge(self.p,on='product_id').groupby('category').agg(revenue=('total_amount','sum'),quantity=('quantity','sum')).reset_index())
    def profile(self,customer):
        z=self.c[self.c.customer_id==customer]
        if z.empty: raise KeyError(customer)
        f=self.s[self.s.customer_id==customer].iloc[0]; cluster=self.summary[self.summary.cluster==f.cluster].iloc[0]
        history=self.t[self.t.customer_id==customer].merge(self.p[['product_id','product_name','category']],on='product_id').sort_values('transaction_date',ascending=False)
        return {'customer':records(z)[0],'features':records(self.f[self.f.customer_id==customer])[0],'cluster':int(f.cluster),'segment':f.segment,'explanation':f'Assigned to {f.segment} using standardized, log-scaled behavior features. Cluster mean recency {cluster.recency:.1f} days, frequency {cluster.frequency:.1f} baskets, spending INR {cluster.monetary:.2f}. Features reflect training cutoff, while purchase history includes all dates.','history':records(history),'recommendations':self.rec.recommend(customer)}
    def relationships(self,customer):
        if customer not in self.g: raise KeyError(customer)
        neighbors=list(self.g.neighbors(customer)); selected=[customer]+neighbors[:35]
        for n in list(selected):
            if self.g.nodes[n].get('type')=='product': selected.extend([b for b in self.g.neighbors(n) if self.g.nodes[b].get('type')=='category'])
        sub=self.g.subgraph(selected)
        return {'nodes':[{'id':n,**attrs} for n,attrs in sub.nodes(data=True)],'edges':[{'source':a,'target':b,**attrs} for a,b,attrs in sub.edges(data=True)]}

@lru_cache(maxsize=1)
def get_store(): return Store()
