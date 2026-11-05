from backend.app.api.dependencies import *

router=APIRouter(tags=["customers"])

@router.get('/api/customers')
def customers(page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),search:str=Query('',max_length=100)):
    s=get_store(); df=s.c.merge(s.s[['customer_id','cluster','segment','monetary','recency']],on='customer_id'); df=df[df.customer_id.str.contains(search,case=False,regex=False)|df.location.str.contains(search,case=False,regex=False)]; return {'items':records(df.iloc[(page-1)*page_size:page*page_size]),'total':len(df),'page':page,'page_size':page_size}


@router.get('/api/customers/{customer_id}')
@router.get('/api/customers/{customer_id}/profile')
def profile(customer_id:str): return customer_exists(customer_id).profile(customer_id)
