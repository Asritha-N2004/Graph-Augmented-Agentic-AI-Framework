"""Run with python -m backend.pipeline --epochs 40; never retrain at API startup."""
import argparse
import os
import json
import time
import shutil
import hashlib
from datetime import datetime,timezone
import pandas as pd
from backend.app.config import DATA,ARTIFACTS,SEED
from backend.ml import data,segmentation,graph,gnn,eda
from backend.ml.recommendation import HybridRecommender

def run(epochs=40,regenerate=False):
    start=time.monotonic()
    if regenerate or not (DATA/'customers.csv').exists(): data.generate()
    c,p,t=data.clean(*data.load()); train,val,test=data.split(t)
    f=data.features(c,p,train); full=data.features(c,p,t)
    for name,frame in [('cleaned_customers',c),('cleaned_transactions',t),('customer_features',full),('processed_customer_features',f),('processed_product_features',pd.get_dummies(p,columns=['category','brand']))]: frame.to_csv(DATA/f'{name}.csv',index=False)
    for name,frame in [('train',train),('validation',val),('test',test)]: frame.to_csv(DATA/f'{name}_transactions.csv',index=False)
    metadata={'seed':SEED,'source':'synthetic','currency':'INR','feature_columns':data.FEATURES,'feature_definitions':{'recency':'days since most recent purchase','frequency':'distinct baskets','monetary':'net spending','average_order_value':'net spending / baskets','product_diversity':'unique products','category_diversity':'unique categories','average_basket_size':'units / baskets','discount_sensitivity':'mean observed line discount; association, not causal sensitivity','tenure_days':'days since registration as of cutoff','purchase_frequency':'baskets per 30 tenure days','clv_proxy':'AOV x monthly frequency x 12; not validated lifetime value'},'train_end':str(train.transaction_date.max()),'validation_end':str(val.transaction_date.max()),'test_end':str(test.transaction_date.max()),'split_rows':[len(train),len(val),len(test)],'created_at':datetime.now(timezone.utc).isoformat()}
    (DATA/'preprocessing_metadata.json').write_text(json.dumps(metadata,indent=2))
    print('Training segmentation',flush=True); segments,summary,sm=segmentation.train(f)
    print('Building training-only graph',flush=True); g,x,edges,mapping=graph.build(c,p,train,segments)
    print('Training GCN, GraphSAGE and GAT',flush=True); embeddings,gm=gnn.train(x,edges,mapping,c,p,[train,val,test],epochs)
    print('Evaluating hybrid and five baselines',flush=True); rec=HybridRecommender().fit(c,p,train,segments,embeddings,mapping); rm=rec.evaluate(test); rec.save()
    rows=[dict(customer_id=cu,**r) for cu in c.customer_id for r in rec.recommend(cu)]; pd.DataFrame(rows).to_csv(ARTIFACTS/'models/recommendations.csv',index=False)
    eda.run(c,p,t,full)
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,5))
    for name in ['gcn','graphsage','gat']: ax.plot([v['validation_loss'] for v in gm[name]['history']],label=name)
    ax.legend(); ax.set(xlabel='Epoch',ylabel='Validation BCE',title='GNN validation learning curves'); fig.tight_layout(); fig.savefig(ARTIFACTS/'eda/gnn_learning.png'); plt.close(fig)
    import networkx as nx
    sample=list(g.nodes)[:12]; sample+=list({b for a in sample for b in g.neighbors(a)})[:80]; sub=g.subgraph(sample)
    fig,ax=plt.subplots(figsize=(12,8)); nx.draw_networkx(sub,nx.spring_layout(sub,seed=SEED),node_size=35,with_labels=False,ax=ax,node_color=['#22b8a8' if sub.nodes[n]['type']=='customer' else '#5967e8' for n in sub]); fig.savefig(ARTIFACTS/'eda/graph.png'); plt.close(fig)
    version=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'); manifest={'version':version,'duration_seconds':time.monotonic()-start,'dataset_sha256':hashlib.sha256((DATA/'transactions.csv').read_bytes()).hexdigest(),**metadata}
    (ARTIFACTS/'models/manifest.json').write_text(json.dumps(manifest,indent=2)); (ARTIFACTS/f'metrics/run_{version}.json').write_text(json.dumps(manifest,indent=2))
    version_dir=ARTIFACTS/'versions'/version
    shutil.copytree(ARTIFACTS/'models',version_dir/'models'); shutil.copytree(ARTIFACTS/'metrics',version_dir/'metrics')
    import mlflow
    mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI','sqlite:///'+str(ARTIFACTS/'mlflow.db')))
    experiment=mlflow.get_experiment_by_name('CIRP synthetic temporal evaluation')
    if experiment is None: mlflow.create_experiment('CIRP synthetic temporal evaluation',artifact_location=(ARTIFACTS/'mlflow-artifacts').resolve().as_uri())
    mlflow.set_experiment('CIRP synthetic temporal evaluation')
    with mlflow.start_run(run_name=version):
        mlflow.log_params({'seed':SEED,'epochs':epochs,'source':'synthetic','version':version,'graph_model':gm['selected_by_validation'],'dataset_sha256':manifest['dataset_sha256']}); mlflow.log_metrics({'segmentation_silhouette':sm['kmeans']['silhouette'],'hybrid_ndcg_at_5':rm['hybrid']['ndcg_at_k'],'duration_seconds':manifest['duration_seconds']}); mlflow.log_artifacts(str(ARTIFACTS/'metrics'),artifact_path='evaluation'); mlflow.log_artifacts(str(ARTIFACTS/'models'),artifact_path='models')
    from backend.app.database import initialize
    initialize()
    from backend.ml.reporting import write_report
    write_report()
    print(json.dumps({'version':version,'hybrid':rm['hybrid'],'selected_gnn':gm['selected_by_validation']},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--epochs',type=int,default=40); parser.add_argument('--regenerate',action='store_true'); args=parser.parse_args(); run(args.epochs,args.regenerate)
