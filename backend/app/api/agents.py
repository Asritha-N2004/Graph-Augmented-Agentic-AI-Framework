from backend.app.api.dependencies import *

router=APIRouter(tags=["agents"])

@router.post('/api/agents/analyze')
@router.post('/api/agents/chat')
def agent(body:AgentRequest):
    if body.customer_id: customer_exists(body.customer_id)
    return analyze(get_store(),body.question,body.customer_id)


@router.get('/api/agents/status')
def status():
    with Session() as db: logs=db.scalars(select(AgentLog).order_by(AgentLog.id.desc()).limit(30)).all(); return {'agents':NAMES,'logs':[{'id':v.id,'run_id':v.run_id,'agent':v.agent,'status':v.status,'created_at':v.created_at} for v in logs]}


@router.get('/api/agents/workflow')
def workflow(): return {'nodes':NAMES,'edges':[['supervisor',n] for n in NAMES[:5]]+[[n,'report_generation'] for n in NAMES[:5]],'routing':'Conditional, based on question intent','retries':2}
