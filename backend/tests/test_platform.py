import json
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import DATA,ARTIFACTS
from backend.app.services import get_store
from backend.ml.data import clean,load,split

@pytest.fixture(scope='module')
def client(): return TestClient(app)

def test_temporal_graph_has_no_heldout_purchases():
    c,p,t=clean(*load()); train,val,test=split(t); store=get_store()
    expected=set(train[['customer_id','product_id']].itertuples(index=False,name=None))
    actual={(a,b) if a.startswith('CUST') else (b,a) for a,b,v in store.g.edges(data=True) if v['relation']=='purchased_and_interacted'}
    assert actual==expected
    assert train.transaction_date.max()<val.transaction_date.min()<test.transaction_date.min()
    from backend.ml.data import features,FEATURES
    pd.testing.assert_frame_equal(features(c,p,train)[FEATURES],store.f[FEATURES],check_exact=False,rtol=1e-8)

def test_recommendation_exclusions_and_explanations():
    s=get_store()
    for cu in s.c.customer_id.iloc[:20]:
        rec=s.rec.recommend(cu); purchased=set(s.rec.products.iloc[np.flatnonzero(s.rec.matrix[s.rec.ci[cu]])].product_id)
        assert len(rec)==5
        assert not purchased.intersection(r['product_id'] for r in rec)
        for r in rec:
            assert abs(r['score']-sum(s.rec.weights[k]*r['components'][k] for k in r['components']))<2e-5
            assert r['reason'] and 'not calibrated' in r['confidence_type']

@pytest.mark.parametrize('path',['/health','/api/customers','/api/customers/CUST_0001','/api/customers/CUST_0001/profile','/api/segmentation/summary','/api/segmentation/clusters','/api/segmentation/metrics','/api/graph/summary','/api/graph/relationships/CUST_0001','/api/graph/similar-customers/CUST_0001','/api/recommendations/CUST_0001','/api/recommendations/metrics','/api/agents/status','/api/agents/workflow','/api/analytics/overview','/api/analytics/revenue','/api/analytics/products','/api/analytics/customers','/api/analytics/eda','/api/models/metrics','/api/reports/summary'])
def test_api_reads(client,path):
    response=client.get(path); assert response.status_code==200,response.text; assert response.json()

def test_validation_and_not_found(client):
    assert client.get('/api/customers?page=0').status_code==422
    assert client.get('/api/recommendations/CUST_0001?k=500').status_code==422
    assert client.get('/api/customers/CUST_9999').status_code==404
    assert client.post('/api/agents/chat',json={'question':'x'}).status_code==422
    assert client.post('/api/segmentation/train',json={'epochs':2}).status_code==403

@pytest.mark.parametrize('question,route',[('Which segment generates the highest revenue?','segmentation'),('Recommend cross-selling products','recommendation'),('Show product combinations','graph_intelligence'),('How can retention improve?','business_intelligence'),('Analyze data quality','data_analyst')])
def test_agents_execute_tools(client,question,route):
    response=client.post('/api/agents/chat',json={'question':question,'customer_id':'CUST_0001'}); assert response.status_code==200,response.text
    result=response.json(); assert result['route']==route; assert result['evidence']; assert [v['agent'] for v in result['logs']]==['supervisor',route,'report_generation']
    assert 'Synthetic' in result['answer']

def test_csv_export(client):
    res=client.post('/api/reports/generate',json={'kind':'segmentation','format':'csv'}); assert res.status_code==200; assert 'cluster' in res.text

def test_evaluation_report_includes_all_model_families(client):
    res=client.post('/api/reports/generate',json={'kind':'evaluation','format':'csv'})
    assert res.status_code==200
    assert all(name in res.text for name in ['kmeans','gcn','graphsage','gat','hybrid'])

def test_metrics_are_real_and_bounded():
    s=get_store(); metrics=s.metrics('recommendation')
    for method in ['hybrid','collaborative','graph','content','copurchase','segment']:
        assert metrics[method]['evaluated_customers']>0
        for k in ['precision_at_k','recall_at_k','map_at_k','ndcg_at_k','catalog_coverage']: assert 0<=metrics[method][k]<=1
    for name in ['gcn','graphsage','gat']:
        assert (ARTIFACTS/f'models/{name}_model.pt').exists()
        assert len(s.metrics('graph_training')[name]['history'])>=2

def test_cold_customers_do_not_collapse_behavior_clusters():
    s=get_store(); cold=s.s[s.s.frequency==0]; active=s.s[s.s.frequency>0]
    assert set(cold.cluster)=={-1}
    assert active.cluster.nunique()>=2
    assert not (active.cluster==-1).any()

def test_preprocessing_deduplicates_and_rejects_broken_keys():
    c,p,t=load(); _,_,cleaned=clean(c,p,pd.concat([t,t.iloc[:1]],ignore_index=True))
    assert len(cleaned)==len(t)
    broken=t.copy(); broken.loc[0,'product_id']='UNKNOWN'
    with pytest.raises(ValueError,match='foreign key'): clean(c,p,broken)

@pytest.mark.parametrize('question,expected',[('Which customers are at risk?','Retention review candidates'),('Which product categories have highest purchase frequency?','unit purchase frequency')])
def test_question_specific_evidence_summary(client,question,expected):
    res=client.post('/api/agents/chat',json={'question':question})
    assert res.status_code==200
    assert expected in res.json()['answer']

def test_service_api_key_is_enforced_when_configured(client,monkeypatch):
    monkeypatch.setenv('BACKEND_API_KEY','test-service-key')
    assert client.get('/health').status_code==200
    assert client.get('/api/analytics/overview').status_code==401
    assert client.get('/api/analytics/overview',headers={'X-CIRP-API-Key':'wrong'}).status_code==401
    assert client.get('/api/analytics/overview',headers={'X-CIRP-API-Key':'test-service-key'}).status_code==200
