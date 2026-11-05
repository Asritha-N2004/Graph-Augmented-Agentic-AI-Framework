import io
import json
import logging
import os
import threading
import uuid
from datetime import datetime,timezone
from typing import Literal
import pandas as pd
from fastapi import APIRouter,HTTPException,Query,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse,StreamingResponse,FileResponse
from pydantic import BaseModel,Field
from sqlalchemy import select
from backend.app.config import ARTIFACTS
from backend.app.database import Base,engine,Session,AgentLog,Report
from backend.app.services import get_store,records
from backend.agents.workflow import analyze,NAMES

class CustomerRequest(BaseModel):
    customer_id:str=Field(pattern=r'^CUST_\d{4,}$')
    k:int=Field(default=5,ge=1,le=50)
    repeat:bool=False


class AgentRequest(BaseModel):
    question:str=Field(min_length=3,max_length=2000)
    customer_id:str|None=Field(default=None,pattern=r'^CUST_\d{4,}$')


class TrainRequest(BaseModel):
    epochs:int=Field(default=40,ge=2,le=200)


class ReportRequest(BaseModel):
    kind:Literal['segmentation','recommendations','business','evaluation']='business'
    format:Literal['csv','pdf']='csv'


def customer_exists(customer):
    s=get_store()
    if customer not in s.rec.ci: raise KeyError(customer)
    return s


training_lock=threading.Lock()
