"""Five independently inspectable signals; scores are not probabilities."""
import json
import joblib
import numpy as np
import pandas as pd
from backend.app.config import ARTIFACTS

def normalize(v):
    v=np.asarray(v,dtype=float); span=v.max()-v.min()
    return (v-v.min())/span if span>1e-10 else np.zeros_like(v)

class HybridRecommender:
    weights={'collaborative':.25,'content':.15,'graph':.25,'copurchase':.2,'segment':.15}
    def fit(self,c,p,t,segments,embeddings,mapping):
        from sklearn.metrics.pairwise import cosine_similarity
        self.customers=list(c.customer_id); self.products=p.reset_index(drop=True); self.ci={a:i for i,a in enumerate(self.customers)}; self.pi={a:i for i,a in enumerate(p.product_id)}
        self.matrix=np.zeros((len(c),len(p)))
        for (cu,pr),n in t.groupby(['customer_id','product_id']).quantity.sum().items(): self.matrix[self.ci[cu],self.pi[pr]]=n
        self.item_similarity=cosine_similarity(self.matrix.T)
        content=pd.get_dummies(p[['category','subcategory','brand']]).astype(float)
        content['price']=normalize(np.log1p(p.price)); self.content_similarity=cosine_similarity(content)
        self.copurchase=np.zeros((len(p),len(p)))
        for _,basket in t.groupby('transaction_id'):
            items=[self.pi[a] for a in basket.product_id.unique()]
            for a in items:
                for b in items:
                    if a!=b: self.copurchase[a,b]+=1
        z=embeddings.numpy(); self.graph_scores=cosine_similarity(z[[mapping[a] for a in self.customers]],z[[mapping[a] for a in p.product_id]])
        self.clusters=segments.set_index('customer_id').cluster.to_dict(); self.segment_scores={}
        for cluster in set(self.clusters.values()): self.segment_scores[cluster]=self.matrix[[self.ci[a] for a in self.customers if self.clusters[a]==cluster]].sum(axis=0)
        return self
    def components(self,customer):
        i=self.ci[customer]; history=self.matrix[i]; profile=history/max(history.sum(),1)
        return {'collaborative':normalize(history@self.item_similarity),'content':normalize(profile@self.content_similarity),'graph':normalize(self.graph_scores[i]),'copurchase':normalize(history@self.copurchase),'segment':normalize(self.segment_scores[self.clusters[customer]])}
    def recommend(self,customer,k=5,repeat=False,method='hybrid'):
        parts=self.components(customer); score=sum(self.weights[key]*value for key,value in parts.items()) if method=='hybrid' else parts[method]
        score=score.copy()
        if not repeat: score[self.matrix[self.ci[customer]]>0]=-np.inf
        indices=[i for i in np.argsort(-score) if np.isfinite(score[i])][:k]; result=[]
        for rank,i in enumerate(indices):
            row=self.products.iloc[i].to_dict(); components={key:round(float(value[i]),5) for key,value in parts.items()}; strongest=max(components,key=components.get)
            reason={'collaborative':'Frequently selected by customers with overlapping purchase histories','content':'Matches the categories, product types and brands in this customer’s history','graph':'Close to this customer in learned graph representation','copurchase':'Purchased in the same baskets as products in this customer’s history','segment':'Popular in this customer’s behavior-derived segment'}[strongest]
            history_indices=np.flatnonzero(self.matrix[self.ci[customer]]>0)
            support=sorted(history_indices,key=lambda j:self.copurchase[j,i],reverse=True)[:3]
            evidence={'training_purchase_count':int(self.matrix[self.ci[customer]].sum()),'supporting_purchases':[{'product_id':self.products.iloc[j].product_id,'product_name':self.products.iloc[j].product_name,'shared_baskets':int(self.copurchase[j,i])} for j in support],'segment_cluster':int(self.clusters[customer]),'graph_signal':'cosine similarity of learned GNN embeddings; normalized within customer'}
            row.update(rank=rank+1,score=round(float(score[i]),5),confidence=round(float(np.mean(list(components.values()))),5),confidence_type='heuristic signal agreement; not calibrated probability',components=components,evidence=evidence,reason=reason); result.append(row)
        return result
    def evaluate(self,test,k=5):
        truth={a:set(g.product_id)-set(self.products.iloc[np.flatnonzero(self.matrix[self.ci[a]]>0)].product_id) for a,g in test.groupby('customer_id') if a in self.ci}
        truth={a:v for a,v in truth.items() if v}; results={}
        for method in ['hybrid','collaborative','content','graph','copurchase','segment']:
            values=[]; covered=set(); diversity=[]
            for cu,relevant in truth.items():
                rec=self.recommend(cu,k,method=method); ids=[v['product_id'] for v in rec]; hits=np.array([v in relevant for v in ids],dtype=float); n=len(hits)
                if not n: continue
                precision=hits.sum()/k; recall=hits.sum()/len(relevant); ap=sum(hits[j]*hits[:j+1].mean() for j in range(n))/min(k,len(relevant)); dcg=sum(hits/np.log2(np.arange(n)+2)); ideal=sum(1/np.log2(np.arange(min(k,len(relevant)))+2))
                values.append([precision,recall,ap,dcg/ideal,float(hits.any())]); covered.update(ids)
                ix=[self.pi[a] for a in ids]; sim=self.content_similarity[np.ix_(ix,ix)]; diversity.append(float((1-sim[np.triu_indices(n,1)]).mean()) if n>1 else 0)
            means=np.mean(values,axis=0) if values else np.zeros(5)
            results[method]=dict(zip(['precision_at_k','recall_at_k','map_at_k','ndcg_at_k','hit_rate_at_k'],map(float,means)))
            results[method].update(catalog_coverage=len(covered)/len(self.products),diversity=float(np.mean(diversity)) if diversity else 0,evaluated_customers=len(values),k=k)
        results['protocol']='Full catalog ranking; excludes training purchases; novel temporal test interactions; no test-based tuning. Synthetic data only.'
        (ARTIFACTS/'metrics/recommendation_metrics.json').write_text(json.dumps(results,indent=2)); return results
    def export_serving(self,directory):
        keys=sorted(self.segment_scores)
        np.savez_compressed(directory/'recommendation_state.npz',matrix=self.matrix,item_similarity=self.item_similarity,content_similarity=self.content_similarity,copurchase=self.copurchase,graph_scores=self.graph_scores,segment_scores=np.stack([self.segment_scores[k] for k in keys]))
        (directory/'recommendation_state.json').write_text(json.dumps({'customers':self.customers,'products':list(self.products.product_id),'clusters':{k:int(v) for k,v in self.clusters.items()},'segment_keys':list(map(int,keys))}))
    @classmethod
    def load_serving(cls,directory,products):
        metadata=json.loads((directory/'recommendation_state.json').read_text());state=np.load(directory/'recommendation_state.npz',allow_pickle=False)
        if list(products.product_id)!=metadata['products']: raise ValueError('Serving catalog does not match trained product order')
        model=cls();model.customers=metadata['customers'];model.products=products.reset_index(drop=True);model.ci={v:i for i,v in enumerate(model.customers)};model.pi={v:i for i,v in enumerate(metadata['products'])};model.clusters=metadata['clusters']
        for name in ['matrix','item_similarity','content_similarity','copurchase','graph_scores']: setattr(model,name,state[name])
        model.segment_scores={key:state['segment_scores'][i] for i,key in enumerate(metadata['segment_keys'])};state.close();return model
    def save(self):
        joblib.dump(self,ARTIFACTS/'models/recommendation_model.pkl');self.export_serving(ARTIFACTS/'models')
