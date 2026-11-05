import json
import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from scipy.cluster.hierarchy import linkage, dendrogram
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from backend.app.config import ARTIFACTS, SEED
from backend.ml.data import FEATURES

def scores(x,y):
    mask=y>=0; labels=y[mask]
    if len(set(labels))<2 or len(set(labels))>=len(labels): return {'silhouette':None,'davies_bouldin':None,'calinski_harabasz':None,'noise':int((~mask).sum())}
    return {'silhouette':float(silhouette_score(x[mask],labels,sample_size=min(1000,len(labels)),random_state=SEED)), 'davies_bouldin':float(davies_bouldin_score(x[mask],labels)), 'calinski_harabasz':float(calinski_harabasz_score(x[mask],labels)), 'noise':int((~mask).sum())}

def train(f):
    # A no-purchase population otherwise dominates silhouette and collapses all
    # purchasing customers into one cluster. Evaluate behavior among active customers.
    active=f.frequency.to_numpy()>0
    scaler=StandardScaler(); x=scaler.fit_transform(np.log1p(f.loc[active,FEATURES].clip(lower=0)))
    candidates=[]
    for k in range(2,8):
        m=KMeans(n_clusters=k,n_init=10,random_state=SEED).fit(x)
        candidates.append((scores(x,m.labels_)['silhouette'],m))
    _,model=max(candidates,key=lambda a:a[0]); y=model.labels_
    metrics={'kmeans':scores(x,y),'elbow':[{'k':m.n_clusters,'inertia':m.inertia_,'silhouette':s} for s,m in candidates]}
    for name,m in [('hierarchical',AgglomerativeClustering(n_clusters=model.n_clusters)),('dbscan',DBSCAN(eps=1.5,min_samples=8))]: metrics[name]=scores(x,m.fit_predict(x))
    xt,xv,yt,yv=train_test_split(x,y,test_size=.2,random_state=SEED,stratify=y)
    surrogate=RandomForestClassifier(n_estimators=100,max_depth=8,random_state=SEED,n_jobs=1).fit(xt,yt)
    metrics['surrogate']={'purpose':'Approximate active-customer cluster assignment; not causal explanation','heldout_fidelity':float(surrogate.score(xv,yv)),'feature_importances':dict(zip(FEATURES,map(float,surrogate.feature_importances_)))}
    joblib.dump(surrogate,ARTIFACTS/'models/segment_surrogate.pkl')
    f=f.copy(); f['cluster']=-1; f.loc[active,'cluster']=y
    summary=f.groupby('cluster')[FEATURES].mean(); summary['customers']=f.groupby('cluster').size(); summary['revenue']=f.groupby('cluster').monetary.sum()
    def label(r):
        if r.monetary>f.monetary.quantile(.7): return 'High-Value Customers'
        if r.recency>f.recency.quantile(.7): return 'At-Risk Customers'
        if r.tenure_days<f.tenure_days.quantile(.3): return 'New Customers'
        if r.frequency>f.frequency.median(): return 'Loyal Customers'
        if r.frequency<f.frequency.quantile(.3): return 'Occasional Customers'
        return 'Regular Customers'
    summary['segment']=summary.apply(label,axis=1)
    if -1 in summary.index: summary.loc[-1,'segment']='No Training Purchases'
    f['segment']=f.cluster.map(summary.segment)
    summary['revenue_share']=summary.revenue/summary.revenue.sum()
    f.to_csv(ARTIFACTS/'models/customer_segments.csv',index=False); summary.reset_index().to_csv(ARTIFACTS/'models/cluster_summary.csv',index=False)
    metrics['population']={'active_customers':int(active.sum()),'no_training_purchases':int((~active).sum()),'cluster_size_distribution':{str(k):int(v) for k,v in f.cluster.value_counts().items()},'revenue_contribution':{str(k):float(v) for k,v in summary.revenue_share.items()}}
    joblib.dump({'model':model,'scaler':scaler,'features':FEATURES,'cold_customer_cluster':-1},ARTIFACTS/'models/segmentation_model.pkl')
    (ARTIFACTS/'metrics/segmentation_metrics.json').write_text(json.dumps(metrics,indent=2))
    fig,axes=plt.subplots(1,2,figsize=(12,4)); axes[0].plot([m.n_clusters for _,m in candidates],[m.inertia_ for _,m in candidates],marker='o'); axes[0].set_title('K-Means elbow'); dendrogram(linkage(x[:200],method='ward'),ax=axes[1],truncate_mode='lastp',p=20); axes[1].set_title('Ward dendrogram (first 200 customers)'); fig.tight_layout(); fig.savefig(ARTIFACTS/'eda/clustering.png'); plt.close(fig)
    return f,summary.reset_index(),metrics
