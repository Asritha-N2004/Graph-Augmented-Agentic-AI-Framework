"""Rebuild a human-readable experiment report directly from measured metrics."""
import json
from backend.app.config import ARTIFACTS

def write_report():
    manifest=json.loads((ARTIFACTS/'models/manifest.json').read_text())
    segmentation=json.loads((ARTIFACTS/'metrics/segmentation_metrics.json').read_text())
    gnn=json.loads((ARTIFACTS/'metrics/graph_training_metrics.json').read_text())
    rec=json.loads((ARTIFACTS/'metrics/recommendation_metrics.json').read_text())
    lines=['# CIRP synthetic experiment report','',f"Model version: {manifest['version']}",'',f"Training cutoff: {manifest['train_end']}. Validation cutoff: {manifest['validation_end']}. Test cutoff: {manifest['test_end']}.",'','All findings are from a seeded simulator, not real-world evidence.','', '## Customer segmentation','','No-purchase customers are an explicit cohort, excluded from behavioral model selection.','', '| Algorithm | Silhouette | Davies-Bouldin | Calinski-Harabasz | Noise |','| --- | ---: | ---: | ---: | ---: |']
    fmt=lambda value: f'{value:.4f}' if value is not None else 'N/A'
    for name in ['kmeans','hierarchical','dbscan']:
        v=segmentation[name]; lines.append(f"| {name} | {fmt(v['silhouette'])} | {fmt(v['davies_bouldin'])} | {fmt(v['calinski_harabasz'])} | {v['noise']} |")
    lines+=['','## Graph link prediction','',f"Selected by validation AUC: {gnn['selected_by_validation']}. Classification uses balanced sampled negatives and novel temporal links; these are not calibrated purchase probabilities.",'','| Model | ROC-AUC | AP | Precision | Recall | F1 | Accuracy |','| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name in ['gcn','graphsage','gat']:
        v=gnn[name]; lines.append('| '+name+' | '+' | '.join(fmt(v[k]) for k in ['roc_auc','average_precision','precision','recall','f1','accuracy'])+' |')
    lines+=['','## Full-catalog recommendation evaluation','','| Method | Precision@5 | Recall@5 | MAP@5 | NDCG@5 | Hit rate@5 | Coverage | Diversity |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name,v in rec.items():
        if isinstance(v,dict): lines.append('| '+name+' | '+' | '.join(fmt(v[k]) for k in ['precision_at_k','recall_at_k','map_at_k','ndcg_at_k','hit_rate_at_k','catalog_coverage','diversity'])+' |')
    best=max((k for k,v in rec.items() if isinstance(v,dict)),key=lambda k:rec[k]['ndcg_at_k'])
    lines+=['',f"Evaluated customers: {rec['hybrid']['evaluated_customers']}. Highest measured NDCG@5: {best}. Fixed hybrid weights were not tuned on the test set.",'','## Limits','','The dataset encodes category preferences and complementary baskets by design. Results measure recovery of simulator patterns. The evaluation is transductive and does not establish new-customer, new-product or real-market generalization. Segment names are heuristic interpretations. Discount association, inactivity and CLV proxies are not causal findings or calibrated forecasts.','']
    path=ARTIFACTS/'reports/experiment-report.md'; path.write_text('\n'.join(lines),encoding='utf-8'); return path
