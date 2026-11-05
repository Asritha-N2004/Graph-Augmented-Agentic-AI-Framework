"""Evidence-producing tools coordinated by a conditional LangGraph supervisor."""
import json
import os
import time
import uuid
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from langgraph.types import RetryPolicy
from backend.app.database import log_agent

class State(TypedDict,total=False):
    question:str
    customer_id:str
    run_id:str
    route:str
    evidence:dict
    answer:str
    logs:list
    error:str

NAMES=['data_analyst','segmentation','graph_intelligence','recommendation','business_intelligence','report_generation','supervisor']

def route_question(q):
    q=q.lower()
    if any(v in q for v in ['recommend','cross-sell','why was','product should']): return 'recommendation'
    if any(v in q for v in ['combination','relationship','similar','graph','co-purchas']): return 'graph_intelligence'
    if any(v in q for v in ['segment','cluster','at risk','at-risk']): return 'segmentation'
    if any(v in q for v in ['revenue','retention','potential','strategy','high-value']): return 'business_intelligence'
    return 'data_analyst'

def build_workflow(store):
    def supervisor(state):
        route=route_question(state['question']); log_agent(state['run_id'],'supervisor','completed',{'route':route}); return {'route':route,'logs':[{'agent':'supervisor','status':'completed','route':route}]}
    def tool(name):
        def execute(state):
            started=time.monotonic(); customer=state.get('customer_id')
            if name=='data_analyst': evidence={'overview':store.overview(),'category_frequency':store.products(),'quality':json.loads((__import__('backend.app.config',fromlist=['ARTIFACTS']).ARTIFACTS/'eda/overview.json').read_text())}
            elif name=='segmentation': evidence={'segments':store.summary.sort_values('revenue',ascending=False).to_dict('records'),'at_risk_customers':store.s[store.s.frequency>0].nlargest(10,'recency')[['customer_id','recency','monetary','segment']].to_dict('records'),'metrics':store.metrics('segmentation')}
            elif name=='graph_intelligence':
                pairs=sorted([{'product_a':a,'product_b':b,'baskets':v['weight']} for a,b,v in store.g.edges(data=True) if v.get('relation')=='co_purchased'],key=lambda r:r['baskets'],reverse=True)[:10]
                evidence={'copurchases':pairs,'relationships':store.relationships(customer) if customer else None}
            elif name=='recommendation': evidence={'customer_id':customer,'recommendations':store.rec.recommend(customer) if customer else [],'requires_customer':not bool(customer),'metrics':store.metrics('recommendation')['hybrid']}
            else: evidence={'segments_by_revenue':store.summary.sort_values('revenue',ascending=False).to_dict('records'),'categories':store.products(),'high_potential':store.s.nlargest(10,'clv_proxy')[['customer_id','clv_proxy','segment']].to_dict('records'),'retention_candidates':store.s.nlargest(10,'recency')[['customer_id','recency','monetary']].to_dict('records')}
            json.dumps(evidence,allow_nan=False)
            log={'agent':name,'status':'completed','duration_ms':round((time.monotonic()-started)*1000)}; log_agent(state['run_id'],name,'completed',evidence)
            return {'evidence':evidence,'logs':state['logs']+[log]}
        def monitored(state):
            try: return execute(state)
            except Exception as exc:
                log_agent(state['run_id'],name,'failed',{'error_type':type(exc).__name__}); raise
        return monitored
    def report(state):
        e=state['evidence']; route=state['route']
        if route=='segmentation':
            if 'risk' in state['question'].lower(): answer='Retention review candidates among customers with training purchases: '+ '; '.join(f"{r['customer_id']} ({r['recency']:.0f} days since purchase, INR {r['monetary']:,.2f} spending)" for r in e['at_risk_customers'][:5])+'. Inactivity is a heuristic flag, not a churn prediction.'
            else:
                top=e['segments'][0]; answer=f"Cluster {top['cluster']} ({top['segment']}) contributes the most training-window revenue: INR {top['revenue']:,.2f} ({top['revenue_share']:.1%}). The most inactive customers and model metrics are included in the evidence."
        elif route=='recommendation': answer='Select a customer to produce personalized cross-selling recommendations.' if e['requires_customer'] else '\n'.join(f"{r['product_name']}: {r['score']:.3f} model score. {r['reason']}." for r in e['recommendations'])
        elif route=='graph_intelligence': answer='Most frequent observed complementary pairs in the training graph: '+ '; '.join(f"{r['product_a']} + {r['product_b']} ({r['baskets']} baskets)" for r in e['copurchases'][:5])
        elif route=='business_intelligence':
            top=e['segments_by_revenue'][0]; answer=f"Prioritize {top['segment']} (cluster {top['cluster']}), contributing INR {top['revenue']:,.2f} in training revenue. Review the listed high-recency customers for retention outreach; CLV proxy ranks spending potential but is not a validated forecast."
        else:
            if 'categor' in state['question'].lower():
                top=max(e['category_frequency'],key=lambda r:r['quantity']); answer=f"{top['category']} has the highest unit purchase frequency: {top['quantity']:,} units across all dates, with INR {top['revenue']:,.2f} net revenue. Unit frequency is not distinct basket count."
            else:
                o=e['overview']; answer=f"The synthetic dataset contains {o['customers']:,} customers, {o['transactions']:,} baskets and INR {o['revenue']:,.2f} revenue. Category frequency and quality findings are attached as evidence."
        # Optional rewriting is grounded in evidence; deterministic output survives provider errors.
        provider='deterministic tools and templates'
        if os.getenv('LLM_API_KEY'):
            try:
                from langchain_openai import ChatOpenAI
                llm=ChatOpenAI(api_key=os.environ['LLM_API_KEY'],base_url=os.getenv('LLM_BASE_URL','https://api.openai.com/v1'),model=os.getenv('LLM_MODEL','gpt-4.1-mini'),temperature=0,timeout=20,max_retries=1)
                answer=llm.invoke([('system','Summarize the supplied synthetic analytics evidence. Use only supplied numbers; no invented causes or forecasts. Say these are synthetic findings.'),('human',json.dumps({'question':state['question'],'evidence':e}))]).content; provider='configured LLM; review evidence for numerical fidelity'
            except Exception: provider='deterministic fallback after LLM error'
        answer+='\nSynthetic-data analysis only; model scores and confidence are not calibrated probabilities.'
        log_agent(state['run_id'],'report_generation','completed',{'provider':provider}); return {'answer':answer,'logs':state['logs']+[{'agent':'report_generation','status':'completed','provider':provider}]}
    graph=StateGraph(State); graph.add_node('supervisor',supervisor); graph.add_edge(START,'supervisor')
    for name in NAMES[:5]: graph.add_node(name,tool(name),retry_policy=RetryPolicy(max_attempts=2)); graph.add_edge(name,'report_generation')
    graph.add_conditional_edges('supervisor',lambda s:s['route'],{name:name for name in NAMES[:5]}); graph.add_node('report_generation',report); graph.add_edge('report_generation',END)
    return graph.compile()

def analyze(store,question,customer_id=None):
    return build_workflow(store).invoke({'question':question,'customer_id':customer_id,'run_id':uuid.uuid4().hex,'logs':[]})
