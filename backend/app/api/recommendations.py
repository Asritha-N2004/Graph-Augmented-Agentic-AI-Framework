from backend.app.api.dependencies import *

router=APIRouter(tags=["recommendations"])

@router.get('/api/recommendations/metrics')
def rec_metrics(): return get_store().metrics('recommendation')


@router.get('/api/recommendations/{customer_id}')
def recommendations(customer_id:str,k:int=Query(5,ge=1,le=50),repeat:bool=False): return customer_exists(customer_id).rec.recommend(customer_id,k,repeat)


@router.post('/api/recommendations/generate')
def generate(body:CustomerRequest): return customer_exists(body.customer_id).rec.recommend(body.customer_id,body.k,body.repeat)
