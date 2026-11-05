"""Normalized operational store; CSV/model artifacts remain the research source."""
import json
from datetime import datetime,timezone
import pandas as pd
from sqlalchemy import create_engine,Column,String,Integer,Float,ForeignKey,Text,event
from sqlalchemy.orm import DeclarativeBase,sessionmaker
from backend.app.config import DATABASE_URL,DATA,ARTIFACTS

engine=create_engine(DATABASE_URL,connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {})
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine,'connect')
    def enable_foreign_keys(conn,_): conn.execute('PRAGMA foreign_keys=ON')
Session=sessionmaker(engine)
class Base(DeclarativeBase): pass
class Customer(Base):
    __tablename__='customers'
    customer_id=Column(String,primary_key=True); age=Column(Integer); gender=Column(String); location=Column(String,index=True); registration_date=Column(String); membership_type=Column(String); income_group=Column(String)
class Product(Base):
    __tablename__='products'
    product_id=Column(String,primary_key=True); product_name=Column(String); category=Column(String,index=True); subcategory=Column(String); price=Column(Float); brand=Column(String); description=Column(Text)
class Transaction(Base):
    __tablename__='transactions'
    transaction_id=Column(String,primary_key=True); product_id=Column(String,ForeignKey('products.product_id'),primary_key=True); customer_id=Column(String,ForeignKey('customers.customer_id'),index=True); transaction_date=Column(String,index=True); quantity=Column(Integer); unit_price=Column(Float); total_amount=Column(Float); discount=Column(Float); payment_method=Column(String)
class Segment(Base):
    __tablename__='customer_segments'
    customer_id=Column(String,ForeignKey('customers.customer_id'),primary_key=True); cluster=Column(Integer,index=True); segment=Column(String)
class Recommendation(Base):
    __tablename__='recommendations'
    customer_id=Column(String,ForeignKey('customers.customer_id'),primary_key=True); product_id=Column(String,ForeignKey('products.product_id'),primary_key=True); score=Column(Float); reason=Column(Text)
class ModelRun(Base):
    __tablename__='model_runs'
    version=Column(String,primary_key=True); metadata_json=Column(Text); created_at=Column(String)
class AgentLog(Base):
    __tablename__='agent_execution_logs'
    id=Column(Integer,primary_key=True,autoincrement=True); run_id=Column(String,index=True); agent=Column(String); status=Column(String); evidence=Column(Text); created_at=Column(String)
class Report(Base):
    __tablename__='reports'
    id=Column(String,primary_key=True); kind=Column(String); path=Column(String); created_at=Column(String)

def initialize():
    Base.metadata.create_all(engine)
    with Session.begin() as db:
        for table in [Recommendation,Segment,Transaction,Product,Customer]: db.query(table).delete()
        for model,file in [(Customer,DATA/'cleaned_customers.csv'),(Product,DATA/'products.csv'),(Transaction,DATA/'cleaned_transactions.csv'),(Segment,ARTIFACTS/'models/customer_segments.csv'),(Recommendation,ARTIFACTS/'models/recommendations.csv')]:
            columns=set(model.__table__.columns.keys()); rows=pd.read_csv(file).to_dict('records'); db.execute(model.__table__.insert(),[{k:v for k,v in row.items() if k in columns} for row in rows])
        manifest=json.loads((ARTIFACTS/'models/manifest.json').read_text()); db.merge(ModelRun(version=manifest['version'],metadata_json=json.dumps(manifest),created_at=manifest['created_at']))

def log_agent(run_id,agent,status,evidence):
    with Session.begin() as db: db.add(AgentLog(run_id=run_id,agent=agent,status=status,evidence=json.dumps(evidence,default=str),created_at=datetime.now(timezone.utc).isoformat()))
