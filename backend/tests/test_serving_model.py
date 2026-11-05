import joblib
import pandas as pd
from backend.app.config import ARTIFACTS,DATA
from backend.ml.recommendation import HybridRecommender

def test_portable_model_matches_original(tmp_path):
    original=joblib.load(ARTIFACTS/'models/recommendation_model.pkl')
    original.export_serving(tmp_path)
    portable=HybridRecommender.load_serving(tmp_path,pd.read_csv(DATA/'products.csv'))
    for customer in original.customers[:20]:
        for repeat in [False,True]:
            assert original.recommend(customer,10,repeat)==portable.recommend(customer,10,repeat)
