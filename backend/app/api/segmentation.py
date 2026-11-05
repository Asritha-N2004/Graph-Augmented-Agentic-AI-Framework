from backend.app.api.dependencies import *

router=APIRouter(tags=["segmentation"])

@router.get('/api/segmentation/summary')
@router.get('/api/segmentation/clusters')
def segments(): return records(get_store().summary)


@router.get('/api/segmentation/metrics')
def segment_metrics(): return get_store().metrics('segmentation')


@router.post('/api/segmentation/train')
def train(body:TrainRequest):
    if not training_lock.acquire(blocking=False): raise HTTPException(409,'Training is already running')
    try:
        # Opt-in maintenance mode: the whole dependent pipeline must be refreshed together.
        if os.getenv('ENABLE_TRAINING_API')!='true': raise HTTPException(403,'Set ENABLE_TRAINING_API=true in a trusted local maintenance environment')
        from backend.pipeline import run
        run(epochs=body.epochs); get_store.cache_clear(); return {'status':'completed','version':get_store().manifest['version']}
    finally: training_lock.release()
