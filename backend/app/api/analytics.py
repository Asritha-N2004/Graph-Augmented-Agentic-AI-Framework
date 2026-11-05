from backend.app.api.dependencies import *

router=APIRouter(tags=["analytics"])

@router.get('/api/analytics/overview')
def overview(): return get_store().overview()


@router.get('/api/analytics/revenue')
def revenue(): return get_store().revenue()


@router.get('/api/analytics/products')
def products(): return get_store().products()


@router.get('/api/analytics/customers')
def customer_analytics():
    s=get_store(); return {'rfm':records(s.s),'locations':records(s.c.groupby('location').size().reset_index(name='customers')),'memberships':records(s.c.groupby('membership_type').size().reset_index(name='customers'))}


@router.get('/api/analytics/eda')
def eda():
    s=get_store(); return {'quality':json.loads((ARTIFACTS/'eda/overview.json').read_text()),'correlation':records(s.f.select_dtypes('number').corr().reset_index()),'rfm':records(s.s),'charts':['distributions.png','correlation.png','retail_overview.png','clustering.png','gnn_learning.png','graph.png']}


@router.get('/api/analytics/charts/{name}')
def chart(name:str):
    if name not in ['distributions.png','correlation.png','retail_overview.png','clustering.png','gnn_learning.png','graph.png']: raise HTTPException(404,'Unknown chart')
    return FileResponse(ARTIFACTS/'eda'/name)


@router.get('/api/models/metrics')
def model_metrics(): return {'segmentation':get_store().metrics('segmentation'),'gnn':get_store().metrics('graph_training'),'recommendation':get_store().metrics('recommendation'),'manifest':get_store().manifest}
