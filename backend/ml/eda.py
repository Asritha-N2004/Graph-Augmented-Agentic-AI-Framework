import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from backend.app.config import ARTIFACTS
from backend.ml.data import FEATURES

def run(c,p,t,f):
    out=ARTIFACTS/'eda'; sns.set_theme(style='whitegrid',palette='muted')
    overview={name:{'rows':len(df),'dtypes':{k:str(v) for k,v in df.dtypes.items()},'missing':df.isna().sum().to_dict(),'duplicate_rows':int(df.duplicated().sum())} for name,df in [('customers',c),('products',p),('transactions',t),('features',f)]}
    overview['outliers']={k:int(((f[k]<f[k].quantile(.25)-1.5*(f[k].quantile(.75)-f[k].quantile(.25)))|(f[k]>f[k].quantile(.75)+1.5*(f[k].quantile(.75)-f[k].quantile(.25)))).sum()) for k in FEATURES}
    (out/'overview.json').write_text(json.dumps(overview,indent=2,default=int))
    fig,axes=plt.subplots(3,4,figsize=(16,10))
    for ax,k in zip(axes.flat,FEATURES): sns.histplot(f[k],ax=ax,bins=30); ax.set_title(k.replace('_',' ').title())
    fig.tight_layout(); fig.savefig(out/'distributions.png'); plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,9)); sns.heatmap(f[FEATURES].corr(),cmap='vlag',center=0,ax=ax); fig.tight_layout(); fig.savefig(out/'correlation.png'); plt.close(fig)
    z=t.merge(p[['product_id','category','product_name']],on='product_id'); monthly=t.groupby(t.transaction_date.dt.to_period('M')).total_amount.sum(); monthly.index=monthly.index.astype(str)
    fig,axes=plt.subplots(2,2,figsize=(14,9)); monthly.plot(ax=axes[0,0],title='Monthly synthetic revenue'); z.groupby('category').total_amount.sum().plot.bar(ax=axes[0,1],title='Revenue by category'); z.groupby('product_name').quantity.sum().nlargest(12).sort_values().plot.barh(ax=axes[1,0],title='Product popularity'); c.membership_type.value_counts().plot.pie(ax=axes[1,1],title='Membership',autopct='%1.0f%%'); fig.tight_layout(); fig.savefig(out/'retail_overview.png'); plt.close(fig)
    px.scatter(f,x='recency',y='monetary',size='frequency',hover_name='customer_id',title='Synthetic customer RFM').write_html(out/'rfm.html',include_plotlyjs=True)
    f[FEATURES].corr().to_csv(out/'correlation.csv')
    (out/'report.md').write_text(f'# Synthetic retail exploratory analysis\n\n{len(c):,} customers, {len(p):,} products, {t.transaction_id.nunique():,} baskets and {len(t):,} transaction lines.\n\nRevenue: {t.total_amount.sum():,.2f} INR. Median customer spending: {f.monetary.median():,.2f}.\n\nMissing values and duplicates are recorded in overview.json. IQR outliers are flagged, retained for high-value customer analysis, and log-scaled for clustering. Dates and referential integrity are validated before analysis.\n\nBehavior reflects the simulator assumptions, not observed market behavior. Recommendation and graph evaluation use a temporal holdout; dashboard revenue covers the complete dataset.\n',encoding='utf-8')
    return overview
