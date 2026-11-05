from backend.app.api.dependencies import *

router=APIRouter(tags=["graph"])

@router.get('/api/graph/summary')
def graph_summary():
    s=get_store(); return {'nodes':s.g.number_of_nodes(),'edges':s.g.number_of_edges(),'node_types':pd.Series([v['type'] for _,v in s.g.nodes(data=True)]).value_counts().to_dict(),'edge_types':pd.Series([v['relation'] for _,_,v in s.g.edges(data=True)]).value_counts().to_dict(),'training_cutoff':s.manifest['train_end']}


@router.get('/api/graph/relationships/{customer_id}')
def relationships(customer_id:str): return customer_exists(customer_id).relationships(customer_id)


@router.get('/api/graph/similar-customers/{customer_id}')
def similar(customer_id:str):
    s=customer_exists(customer_id); ids=[n for n in s.g.neighbors(customer_id) if s.g.nodes[n]['type']=='customer']; return records(s.s[s.s.customer_id.isin(ids)])
