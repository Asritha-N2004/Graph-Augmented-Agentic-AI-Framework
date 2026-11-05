import io
import json
import logging
import os
import secrets
import threading
import uuid
from datetime import datetime,timezone
from typing import Literal
import pandas as pd
from fastapi import FastAPI,HTTPException,Query,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse,StreamingResponse,FileResponse
from pydantic import BaseModel,Field
from sqlalchemy import select
from backend.app.config import ARTIFACTS
from backend.app.database import Base,engine,Session,AgentLog,Report
from backend.app.services import get_store,records
from backend.agents.workflow import analyze,NAMES

logging.basicConfig(level=logging.INFO); log=logging.getLogger('cirp')
app=FastAPI(title='Customer Intelligence & Recommendation Platform',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:3000').split(','),allow_methods=['GET','POST'],allow_headers=['*'])
Base.metadata.create_all(engine)

@app.middleware('http')
async def service_auth(request:Request,call_next):
    required=os.getenv('BACKEND_API_KEY')
    if os.getenv('VERCEL')=='1' and request.url.path.startswith('/api/') and not required:
        return JSONResponse(status_code=503,content={'detail':'Backend service authentication is not configured.'})
    if required and request.url.path.startswith('/api/') and request.method!='OPTIONS':
        supplied=request.headers.get('X-CIRP-API-Key','')
        if not secrets.compare_digest(supplied.encode(),required.encode()):
            return JSONResponse(status_code=401,content={'detail':'Authentication required.'})
    return await call_next(request)

@app.exception_handler(KeyError)
async def missing(_,exc): return JSONResponse(status_code=404,content={'detail':f'Unknown identifier: {exc.args[0]}'})
@app.exception_handler(FileNotFoundError)
async def not_trained(_,exc): return JSONResponse(status_code=503,content={'detail':'Model artifacts unavailable. Run python -m backend.pipeline first.'})
@app.exception_handler(Exception)
async def error(_,exc):
    log.exception('Request failed'); return JSONResponse(status_code=500,content={'detail':'Operation failed. Check backend logs.'})

@app.get('/health')
def health(): return {'status':'ok','models_ready':(ARTIFACTS/'models/manifest.json').exists()}


from backend.app.api import customers,segmentation,graph,recommendations,agents,analytics,reports
for module in [customers,segmentation,graph,recommendations,agents,analytics,reports]:
    app.include_router(module.router)
