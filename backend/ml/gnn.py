import copy
import json
import numpy as np
import torch
from torch import nn
from torch_geometric.nn import GCNConv,SAGEConv,GATConv
from sklearn.metrics import roc_auc_score,average_precision_score,precision_score,recall_score,f1_score,accuracy_score
from backend.app.config import ARTIFACTS, SEED

class LinkModel(nn.Module):
    def __init__(self,kind,dim,hidden=32):
        super().__init__(); conv={'gcn':GCNConv,'graphsage':SAGEConv,'gat':GATConv}[kind]
        self.a=conv(dim,hidden); self.b=conv(hidden,hidden)
    def forward(self,x,edges): return self.b(torch.relu(self.a(x,edges)),edges)
    @staticmethod
    def score(z,pairs): return (z[pairs[0]]*z[pairs[1]]).sum(-1)

def train(x,edges,mapping,c,p,splits,epochs=40):
    torch.manual_seed(SEED); torch.set_num_threads(2); rng=np.random.default_rng(SEED)
    # Novel links: one split per customer-product pair; repeated pairs are not new links.
    seen=set(); positives=[]
    for frame in splits:
        pairs={(mapping[a],mapping[b]) for a,b in frame[['customer_id','product_id']].itertuples(index=False,name=None)}-seen
        positives.append(sorted(pairs)); seen.update(pairs)
    all_pairs=seen
    customers=[mapping[a] for a in c.customer_id]; products=[mapping[a] for a in p.product_id]
    def samples(pos):
        neg=set()
        while len(neg)<len(pos):
            pair=(int(rng.choice(customers)),int(rng.choice(products)))
            if pair not in all_pairs: neg.add(pair)
        return torch.tensor(pos+sorted(neg),dtype=torch.long).T,torch.cat([torch.ones(len(pos)),torch.zeros(len(pos))])
    batches=[samples(pos) for pos in positives]
    results={}; best_z=None; best_auc=-1
    for kind in ['gcn','graphsage','gat']:
        model=LinkModel(kind,x.shape[1]); optimizer=torch.optim.Adam(model.parameters(),lr=.005,weight_decay=1e-4)
        best=None; best_loss=float('inf'); stale=0; history=[]
        for epoch in range(epochs):
            model.train(); optimizer.zero_grad(); z=model(x,edges); loss=nn.functional.binary_cross_entropy_with_logits(model.score(z,batches[0][0]),batches[0][1]); loss.backward(); optimizer.step()
            model.eval()
            with torch.no_grad(): val=nn.functional.binary_cross_entropy_with_logits(model.score(model(x,edges),batches[1][0]),batches[1][1]).item()
            history.append({'epoch':epoch+1,'train_loss':loss.item(),'validation_loss':val})
            if val<best_loss: best_loss=val; best=copy.deepcopy(model.state_dict()); stale=0
            else: stale+=1
            if stale>=7: break
        model.load_state_dict(best); model.eval()
        with torch.no_grad(): z=model(x,edges); prediction=torch.sigmoid(model.score(z,batches[2][0])).numpy(); vp=torch.sigmoid(model.score(z,batches[1][0])).numpy()
        target=batches[2][1].numpy(); binary=prediction>=.5
        metrics={'roc_auc':float(roc_auc_score(target,prediction)),'average_precision':float(average_precision_score(target,prediction)),'precision':float(precision_score(target,binary,zero_division=0)),'recall':float(recall_score(target,binary,zero_division=0)),'f1':float(f1_score(target,binary,zero_division=0)),'accuracy':float(accuracy_score(target,binary)),'validation_auc':float(roc_auc_score(batches[1][1],vp)),'history':history}
        results[kind]=metrics; torch.save({'state_dict':best,'input_dim':x.shape[1],'hidden':32,'kind':kind},ARTIFACTS/f'models/{kind}_model.pt')
        if metrics['validation_auc']>best_auc: best_auc=metrics['validation_auc']; best_z=z.detach(); selected=kind
    torch.save(best_z,ARTIFACTS/'models/graph_embeddings.pt'); results['selected_by_validation']=selected; results['split_positive_counts']=[len(v) for v in positives]
    (ARTIFACTS/'metrics/graph_training_metrics.json').write_text(json.dumps(results,indent=2))
    return best_z,results
