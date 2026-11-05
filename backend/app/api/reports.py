from backend.app.api.dependencies import *

router=APIRouter(tags=["reports"])

@router.get('/api/reports/summary')
def reports():
    with Session() as db: rows=db.scalars(select(Report).order_by(Report.created_at.desc()).limit(100)).all(); return {'overview':get_store().overview(),'reports':[{'id':r.id,'kind':r.kind,'created_at':r.created_at} for r in rows]}


@router.post('/api/reports/generate')
def report(body:ReportRequest):
    s=get_store(); ident=uuid.uuid4().hex; path=ARTIFACTS/f'reports/{ident}.{body.format}'
    if body.kind=='segmentation': df=s.summary
    elif body.kind=='recommendations': df=pd.read_csv(ARTIFACTS/'models/recommendations.csv').drop(columns=['components'])
    elif body.kind=='evaluation':
        rows=[]
        for task,metric_file,names in [('segmentation','segmentation',['kmeans','hierarchical','dbscan']),('link prediction','graph_training',['gcn','graphsage','gat']),('recommendation','recommendation',['hybrid','collaborative','content','graph','copurchase','segment'])]:
            measured=s.metrics(metric_file)
            for name in names:
                rows.extend({'model':name,'task':task,'metric':key,'value':value} for key,value in measured[name].items() if isinstance(value,(int,float)))
        df=pd.DataFrame(rows)
    else:
        rows=[{'dimension':'all data','group':'Overview','customers':len(s.c),'revenue':s.overview()['revenue']}]
        rows.extend({'dimension':'training segment','group':f"{r['cluster']}: {r['segment']}",'customers':r['customers'],'revenue':r['revenue']} for r in records(s.summary))
        rows.extend({'dimension':'all-date category','group':r['category'],'customers':None,'revenue':r['revenue']} for r in s.products())
        df=pd.DataFrame(rows)
    if body.format=='csv': df.to_csv(path,index=False)
    else:
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle
        from reportlab.lib.pagesizes import landscape,A4
        styles=getSampleStyleSheet(); doc=SimpleDocTemplate(str(path),pagesize=landscape(A4),rightMargin=28,leftMargin=28)
        columns={'segmentation':['cluster','segment','customers','recency','frequency','monetary','revenue','revenue_share'],'recommendations':['customer_id','product_name','score','confidence','reason'],'business':['dimension','group','customers','revenue'],'evaluation':['model','task','metric','value']}[body.kind]
        rows=[[Paragraph(str(k).replace('_',' '),styles['BodyText']) for k in columns]]
        for row in df[columns].head(200).itertuples(index=False,name=None): rows.append([Paragraph('N/A' if pd.isna(v) else str(round(v,3)) if isinstance(v,float) else str(v),styles['BodyText']) for v in row])
        table=LongTable(rows,repeatRows=1,colWidths=[(landscape(A4)[0]-56)/len(columns)]*len(columns)); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9eff5')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.lightgrey),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        doc.build([Paragraph('CIRP | '+body.kind.title()+' report',styles['Title']),Paragraph('Synthetic data only | INR | model version '+s.manifest['version'],styles['BodyText']),Paragraph('PDF contains the first 200 rows and 8 columns. Download CSV for the complete dataset.',styles['BodyText']),Spacer(1,16),table])
    with Session.begin() as db: db.add(Report(id=ident,kind=body.kind,path=str(path),created_at=datetime.now(timezone.utc).isoformat()))
    return FileResponse(path,filename=f'cirp-{body.kind}.{body.format}',media_type='text/csv' if body.format=='csv' else 'application/pdf')
