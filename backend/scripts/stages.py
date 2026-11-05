"""Individual reproducible research stages. Run full pipeline after changing data."""
import argparse
import json
import pandas as pd
import torch
from backend.app.config import DATA,ARTIFACTS
from backend.ml import data,segmentation,graph,gnn,eda
from backend.ml.recommendation import HybridRecommender

def run(stage):
    parser=argparse.ArgumentParser(); parser.add_argument('--epochs',type=int,default=40); args=parser.parse_args()
    if stage=='generate_data': data.generate(); return
    c,p,t=data.clean(*data.load()); train,val,test=data.split(t); f=data.features(c,p,train)
    if stage=='preprocess':
        for name,z in [('cleaned_customers',c),('cleaned_transactions',t),('customer_features',data.features(c,p,t)),('processed_customer_features',f),('processed_product_features',pd.get_dummies(p,columns=['category','brand']))]: z.to_csv(DATA/f'{name}.csv',index=False)
    elif stage=='run_eda': eda.run(c,p,t,data.features(c,p,t))
    elif stage=='train_segmentation': segmentation.train(f)
    elif stage=='build_graph': graph.build(c,p,train,pd.read_csv(ARTIFACTS/'models/customer_segments.csv'))
    elif stage=='train_gnn':
        mapping=json.loads((ARTIFACTS/'graph/node_mapping.json').read_text()); gnn.train(torch.load(ARTIFACTS/'graph/node_features.pt',weights_only=True),torch.load(ARTIFACTS/'graph/edge_index.pt',weights_only=True),mapping,c,p,[train,val,test],args.epochs)
    elif stage=='train_recommender':
        mapping=json.loads((ARTIFACTS/'graph/node_mapping.json').read_text()); rec=HybridRecommender().fit(c,p,train,pd.read_csv(ARTIFACTS/'models/customer_segments.csv'),torch.load(ARTIFACTS/'models/graph_embeddings.pt',weights_only=True),mapping); rec.save(); rec.evaluate(test)
    elif stage=='evaluate':
        import joblib
        print(json.dumps(joblib.load(ARTIFACTS/'models/recommendation_model.pkl').evaluate(test),indent=2))
