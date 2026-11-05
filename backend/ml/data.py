"""Privacy-safe behavioral retail simulator and time-aware preprocessing."""
import json
import numpy as np
import pandas as pd
from backend.app.config import DATA, SEED

CATEGORIES = {
    'Technology': ['Laptop', 'Mouse', 'Keyboard', 'USB Hub', 'Laptop Bag', 'Headphones'],
    'Fitness': ['Yoga Mat', 'Water Bottle', 'Resistance Band', 'Sports Bag', 'Foam Roller', 'Dumbbells'],
    'Home': ['Coffee Maker', 'Coffee Beans', 'Mug', 'Grinder', 'Storage Jar', 'Kettle'],
    'Outdoors': ['Tent', 'Sleeping Bag', 'Lantern', 'Backpack', 'Hiking Boots', 'Compass'],
    'Beauty': ['Cleanser', 'Moisturizer', 'Sunscreen', 'Serum', 'Toner', 'Travel Kit'],
}

def generate(customers=1000, transactions=8000, seed=SEED):
    rng = np.random.default_rng(seed)
    products = []
    for c, names in CATEGORIES.items():
        for variant in range(4):
            for i, name in enumerate(names):
                price = round((18 + 15*i + (400 if name == 'Laptop' else 0))*(1+variant*.35), 2)
                products.append([f'PROD_{len(products)+1:03}', f'{name} {['Essential','Plus','Pro','Elite'][variant]}', c, name, price, ['Northstar','Fieldwork','Forma','Arc'][variant], f'{c} collection: {name}'])
    p = pd.DataFrame(products, columns=['product_id','product_name','category','subcategory','price','brand','description'])
    end = pd.Timestamp('2026-10-31')
    c = pd.DataFrame({'customer_id':[f'CUST_{i+1:04}' for i in range(customers)], 'age':rng.integers(18,76,customers), 'gender':rng.choice(['Female','Male','Unspecified'],customers), 'location':rng.choice(['Hyderabad','Bengaluru','Mumbai','Delhi','Chennai'],customers), 'registration_date':[(end-pd.Timedelta(days=int(d))).date() for d in rng.integers(60,900,customers)], 'membership_type':rng.choice(['Standard','Silver','Gold'],customers,p=[.5,.3,.2]), 'income_group':rng.choice(['Low','Middle','High'],customers,p=[.2,.6,.2])})
    preference = rng.integers(0,5,customers)
    activity = rng.lognormal(0,.8,customers)
    selected = rng.choice(customers,transactions,p=activity/activity.sum())
    rows=[]
    for t, ci in enumerate(selected):
        cat = preference[ci] if rng.random()<.82 else rng.integers(0,5)
        # Common complementary basket pairs, with repeats within preferred categories.
        base = int(rng.choice([0,2,4]))
        age = int((end-pd.Timestamp(c.iloc[ci].registration_date)).days)
        day = end-pd.Timedelta(days=int(rng.integers(0,min(age,365))))
        variant = int(rng.choice(4,p=[.5,.3,.15,.05]))
        basket = [base,base+1] if rng.random()<.55 else [int(rng.integers(0,6))]
        for index in basket:
            product = p.iloc[int(cat)*24+variant*6+index]
            qty=int(rng.choice([1,2,3],p=[.8,.15,.05])); discount=float(rng.choice([0,.05,.1,.2],p=[.6,.15,.2,.05]))
            rows.append([f'TXN_{t+1:06}',c.iloc[ci].customer_id,product.product_id,day.isoformat(),qty,product.price,round(qty*product.price*(1-discount),2),discount,rng.choice(['Card','UPI','Cash'])])
    tx=pd.DataFrame(rows,columns=['transaction_id','customer_id','product_id','transaction_date','quantity','unit_price','total_amount','discount','payment_method'])
    interactions=tx.groupby(['customer_id','product_id']).agg(interaction_count=('quantity','sum'),interaction_timestamp=('transaction_date','max')).reset_index()
    interactions['interaction_type']='purchase'
    for name,df in [('customers',c),('products',p),('transactions',tx),('customer_product_interactions',interactions)]: df.to_csv(DATA/f'{name}.csv',index=False)
    (DATA/'provenance.json').write_text(json.dumps({'source':'entirely synthetic; no real individuals','seed':seed,'as_of':str(end.date()),'license':'CC0-1.0','transactions_are_baskets':True},indent=2))
    return c,p,tx

def load():
    return tuple(pd.read_csv(DATA/f'{name}.csv') for name in ['customers','products','transactions'])

def clean(c,p,t):
    c=c.drop_duplicates('customer_id').copy(); p=p.drop_duplicates('product_id').copy()
    t=t.drop_duplicates(['transaction_id','product_id']).copy()
    for col in ['quantity','unit_price','discount','total_amount']: t[col]=pd.to_numeric(t[col],errors='coerce')
    t['transaction_date']=pd.to_datetime(t.transaction_date,errors='coerce')
    t=t.dropna(subset=['customer_id','product_id','transaction_date','quantity','unit_price','total_amount','discount'])
    t=t[(t.quantity>0)&(t.unit_price>0)&(t.total_amount>=0)&t.discount.between(0,1)]
    if not t.customer_id.isin(c.customer_id).all() or not t.product_id.isin(p.product_id).all(): raise ValueError('Unknown customer/product foreign key')
    if not np.allclose(t.total_amount,t.quantity*t.unit_price*(1-t.discount),atol=.011): raise ValueError('Invalid transaction totals')
    for col in c.columns:
        if col not in ['customer_id','registration_date','age']: c[col]=c[col].fillna('Unknown')
    c['age']=pd.to_numeric(c.age,errors='coerce').fillna(c.age.median())
    c['registration_date']=pd.to_datetime(c.registration_date,errors='coerce')
    if c.registration_date.isna().any(): raise ValueError('Invalid registration dates')
    return c,p,t.sort_values(['transaction_date','transaction_id'])

def split(t):
    days=sorted(t.transaction_date.unique()); a=days[int(len(days)*.7)]; b=days[int(len(days)*.85)]
    return t[t.transaction_date<a].copy(),t[(t.transaction_date>=a)&(t.transaction_date<b)].copy(),t[t.transaction_date>=b].copy()

FEATURES=['recency','frequency','monetary','average_order_value','product_diversity','category_diversity','average_basket_size','discount_sensitivity','tenure_days','purchase_frequency','clv_proxy']

def features(c,p,t,as_of=None):
    as_of=pd.Timestamp(as_of) if as_of is not None else t.transaction_date.max()+pd.Timedelta(days=1)
    z=t.merge(p[['product_id','category']],on='product_id')
    f=z.groupby('customer_id').agg(last_purchase=('transaction_date','max'),frequency=('transaction_id','nunique'),monetary=('total_amount','sum'),product_diversity=('product_id','nunique'),category_diversity=('category','nunique'),units=('quantity','sum'),discount_sensitivity=('discount','mean'))
    f=c[['customer_id','registration_date']].set_index('customer_id').join(f)
    f['recency']=(as_of-f.last_purchase).dt.days.fillna((as_of-f.registration_date).dt.days.clip(lower=0))
    f['tenure_days']=(as_of-f.registration_date).dt.days.clip(lower=1)
    f=f.fillna({'frequency':0,'monetary':0,'product_diversity':0,'category_diversity':0,'units':0,'discount_sensitivity':0})
    f['average_order_value']=f.monetary/f.frequency.clip(lower=1)
    f['average_basket_size']=f.units/f.frequency.clip(lower=1)
    f['purchase_frequency']=f.frequency/f.tenure_days*30
    f['clv_proxy']=f.average_order_value*f.purchase_frequency*12
    for col,ascending in [('recency',False),('frequency',True),('monetary',True)]: f[col+'_score']=pd.qcut(f[col].rank(method='first',ascending=ascending),5,labels=False)+1
    f['rfm_score']=f[[x+'_score' for x in ['recency','frequency','monetary']]].sum(axis=1)
    return f.drop(columns=['last_purchase','registration_date']).reset_index()
