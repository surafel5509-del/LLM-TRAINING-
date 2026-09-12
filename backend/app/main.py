from pathlib import Path
from datetime import datetime
from multiprocessing import Process
import json, shutil, time
import psutil, torch
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from .core import settings, CPU_COUNT
from .db import get_db, SessionLocal
from .models import Project, Dataset, Model, TrainingRun, Metric, Checkpoint, ModelVersion
from .ml import train_run, load_tabular, MLP

app=FastAPI(title='Real ML Training Platform',version='0.2.0')
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
processes={}
class ProjectIn(BaseModel): name:str=Field(min_length=1,max_length=200)
class ModelIn(BaseModel): project_id:str; name:str; task:str='classification'; input_size:int|None=None; output_size:int|None=None; hidden_layers:list[int]=[64,32]; activation:str='relu'; dropout:float=0.0
class TrainIn(BaseModel): project_id:str; dataset_id:str; model_id:str; target:str; task:str; hidden_layers:list[int]=[64,32]; activation:str='relu'; dropout:float=0.0; optimizer:str='adam'; learning_rate:float=1e-3; weight_decay:float=0.0; batch_size:int=32; epochs:int=10; train_ratio:float=0.7; val_ratio:float=0.15; test_ratio:float=0.15; seed:int=42; cpu_workers:int=1; threads:int=1
class InferIn(BaseModel): features:list[float]
def safe_name(name): return Path(name).name.replace(' ','_')
@app.get('/api/health')
def health(): return {'status':'ok','device':'cpu','cpu_cores':CPU_COUNT,'torch_version':torch.__version__}
@app.get('/api/system/resources')
def resources():
    vm=psutil.virtual_memory(); disk=psutil.disk_usage(str(settings.storage_root)); return {'cpu_percent':psutil.cpu_percent(.05),'ram_percent':vm.percent,'ram_bytes':vm.total,'disk_percent':disk.percent,'cpu_cores':CPU_COUNT}
@app.post('/api/projects')
def create_project(payload:ProjectIn,db:Session=Depends(get_db)):
    p=Project(name=payload.name); db.add(p); db.commit(); db.refresh(p); return {'id':p.id,'name':p.name}
@app.get('/api/projects')
def projects(db:Session=Depends(get_db)): return [{'id':p.id,'name':p.name} for p in db.query(Project).order_by(Project.created_at.desc()).all()]
@app.post('/api/datasets')
def upload_dataset(project_id:str,file:UploadFile=File(...),db:Session=Depends(get_db)):
    ext=Path(file.filename or '').suffix.lower()
    if ext not in {'.csv','.json','.jsonl'}: raise HTTPException(400,'Only CSV, JSON and JSONL are currently implemented')
    data=file.file.read()
    if len(data)>settings.max_upload_mb*1024*1024: raise HTTPException(413,'File exceeds upload limit')
    ds=Dataset(project_id=project_id,name=safe_name(file.filename or 'dataset'),format=ext.lstrip('.'),path=''); db.add(ds); db.flush(); path=settings.storage_root/'datasets'/ds.id; path.mkdir(parents=True,exist_ok=True); fp=path/safe_name(file.filename or 'dataset'); fp.write_bytes(data); ds.path=str(fp)
    try:
        import pandas as pd; df=pd.read_csv(fp) if ext=='.csv' else pd.read_json(fp,lines=ext=='.jsonl'); ds.rows=len(df); ds.columns=len(df.columns)
    except Exception as e: db.rollback(); shutil.rmtree(path,ignore_errors=True); raise HTTPException(400,f'Invalid dataset: {e}')
    db.commit(); db.refresh(ds); return {'id':ds.id,'name':ds.name,'rows':ds.rows,'columns':ds.columns}
@app.get('/api/datasets')
def datasets(project_id:str|None=None,db:Session=Depends(get_db)):
    q=db.query(Dataset); q=q.filter(Dataset.project_id==project_id) if project_id else q; return [{'id':d.id,'project_id':d.project_id,'name':d.name,'rows':d.rows,'columns':d.columns,'format':d.format} for d in q.all()]
@app.post('/api/datasets/{dataset_id}/validate')
def validate_dataset(dataset_id:str,target:str,db:Session=Depends(get_db)):
    d=db.get(Dataset,dataset_id)
    if not d: raise HTTPException(404,'Dataset not found')
    try:
        import pandas as pd; raw=pd.read_csv(d.path) if d.format=='csv' else pd.read_json(d.path,lines=d.format=='jsonl'); load_tabular(Path(d.path),target)
        return {'valid':True,'rows':len(raw),'columns':list(raw.columns),'missing':int(raw.isna().sum().sum()),'duplicates':int(raw.duplicated().sum()),'target':target,'target_values':raw[target].value_counts(dropna=False).to_dict()}
    except Exception as e: return {'valid':False,'errors':[str(e)]}
@app.post('/api/models')
def create_model(payload:ModelIn,db:Session=Depends(get_db)):
    if payload.task not in {'classification','regression'}: raise HTTPException(400,'Only classification and regression are implemented')
    m=Model(project_id=payload.project_id,name=payload.name,task=payload.task,architecture=payload.model_dump()); db.add(m); db.commit(); db.refresh(m); return {'id':m.id,'name':m.name,'architecture':m.architecture}
@app.get('/api/models')
def models(project_id:str|None=None,db:Session=Depends(get_db)):
    q=db.query(Model); q=q.filter(Model.project_id==project_id) if project_id else q; return [{'id':m.id,'name':m.name,'task':m.task,'architecture':m.architecture} for m in q.all()]
@app.get('/api/models/{model_id}/versions')
def model_versions(model_id:str,db:Session=Depends(get_db)): return [{'id':v.id,'version':v.version,'run_id':v.run_id,'checkpoint_path':v.checkpoint_path,'metrics':v.metrics,'created_at':v.created_at} for v in db.query(ModelVersion).filter(ModelVersion.model_id==model_id).order_by(ModelVersion.version).all()]
@app.post('/api/training/runs')
def create_run(payload:TrainIn,db:Session=Depends(get_db)):
    if payload.learning_rate<=0 or payload.batch_size<1 or payload.epochs<1: raise HTTPException(400,'Invalid training configuration')
    if abs(payload.train_ratio+payload.val_ratio+payload.test_ratio-1)>1e-6: raise HTTPException(400,'Train/validation/test ratios must sum to 1')
    if payload.cpu_workers<0 or payload.threads<0: raise HTTPException(400,'CPU settings cannot be negative')
    run=TrainingRun(project_id=payload.project_id,dataset_id=payload.dataset_id,model_id=payload.model_id,status='QUEUED',config=payload.model_dump()); db.add(run); db.commit(); db.refresh(run); return {'id':run.id,'status':run.status}
@app.get('/api/training/runs')
def runs(db:Session=Depends(get_db)): return [{'id':r.id,'status':r.status,'error':r.error,'started_at':r.started_at,'finished_at':r.finished_at} for r in db.query(TrainingRun).order_by(TrainingRun.finished_at.desc().nullslast()).all()]
def _worker(run_id):
    db=SessionLocal()
    try: train_run(db,run_id)
    except Exception: pass
    finally: db.close()
@app.post('/api/training/runs/{run_id}/start')
def start_run(run_id:str,db:Session=Depends(get_db)):
    r=db.get(TrainingRun,run_id)
    if not r: raise HTTPException(404,'Run not found')
    if r.status not in {'QUEUED','PAUSED'}: raise HTTPException(409,f'Cannot start from {r.status}')
    if run_id in processes and processes[run_id].is_alive(): return {'status':'already_running'}
    p=Process(target=_worker,args=(run_id,),daemon=True); p.start(); processes[run_id]=p; return {'status':'started'}
@app.post('/api/training/runs/{run_id}/pause')
def pause_run(run_id:str,db:Session=Depends(get_db)):
    if not db.get(TrainingRun,run_id): raise HTTPException(404,'Run not found')
    p=settings.storage_root/'runs'/run_id; p.mkdir(parents=True,exist_ok=True); (p/'pause').touch(); return {'status':'PAUSED'}
@app.post('/api/training/runs/{run_id}/resume')
def resume_run(run_id:str,db:Session=Depends(get_db)):
    p=settings.storage_root/'runs'/run_id; (p/'pause').unlink(missing_ok=True); return start_run(run_id,db)
@app.post('/api/training/runs/{run_id}/cancel')
def cancel_run(run_id:str,db:Session=Depends(get_db)):
    if not db.get(TrainingRun,run_id): raise HTTPException(404,'Run not found')
    p=settings.storage_root/'runs'/run_id; p.mkdir(parents=True,exist_ok=True); (p/'cancel').touch(); return {'status':'CANCELLED'}
@app.get('/api/training/runs/{run_id}/metrics')
def metrics(run_id:str,db:Session=Depends(get_db)): return [{'epoch':m.epoch,'split':m.split,'loss':m.loss,'metric':m.metric,'learning_rate':m.learning_rate,'samples_per_sec':m.samples_per_sec} for m in db.query(Metric).filter(Metric.run_id==run_id).order_by(Metric.epoch,Metric.split).all()]
@app.get('/api/training/runs/{run_id}/checkpoints')
def checkpoints(run_id:str,db:Session=Depends(get_db)): return [{'id':c.id,'epoch':c.epoch,'path':c.path,'is_best':c.is_best,'exists':Path(c.path).exists()} for c in db.query(Checkpoint).filter(Checkpoint.run_id==run_id).all()]
@app.get('/api/runs/{run_id}/test-metrics')
def test_metrics(run_id:str):
    p=settings.storage_root/'runs'/run_id/'test_metrics.json'
    if not p.exists(): raise HTTPException(404,'Test evaluation not available yet')
    return json.loads(p.read_text())
@app.post('/api/models/{model_id}/infer')
def infer(model_id:str,payload:InferIn,db:Session=Depends(get_db)):
    v=db.query(ModelVersion).filter(ModelVersion.model_id==model_id).order_by(ModelVersion.version.desc()).first()
    if not v or not Path(v.checkpoint_path).exists(): raise HTTPException(404,'No trained model version exists')
    ck=torch.load(v.checkpoint_path,map_location='cpu',weights_only=True); cfg=ck['config']; model=MLP(ck['input_size'],ck['output_size'],cfg['hidden_layers'],cfg['activation'],cfg['dropout']); model.load_state_dict(ck['model_state']); model.eval()
    if len(payload.features)!=ck['input_size']: raise HTTPException(400,f'Expected {ck["input_size"]} features')
    x=torch.tensor(payload.features,dtype=torch.float32); scale=torch.tensor(ck['scaler_scale'],dtype=torch.float32); mean=torch.tensor(ck['scaler_mean'],dtype=torch.float32); x=(x-mean)/scale; t=time.perf_counter(); out=model(x.view(1,-1)); elapsed=(time.perf_counter()-t)*1000
    if cfg['task']=='regression': result={'prediction':float(out.item())}
    else:
        probs=torch.softmax(out,dim=1)[0]; idx=int(torch.argmax(probs)); result={'prediction':ck['labels'][idx] if ck['labels'] else idx,'probabilities':probs.tolist(),'confidence':float(probs[idx])}
    result['inference_ms']=elapsed; result['model_version']=v.version; return result
@app.get('/api/checkpoints/{checkpoint_id}/download')
def download_checkpoint(checkpoint_id:str,db:Session=Depends(get_db)):
    c=db.get(Checkpoint,checkpoint_id)
    if not c or not Path(c.path).exists(): raise HTTPException(404,'Checkpoint not found')
    return FileResponse(c.path,media_type='application/octet-stream',filename=Path(c.path).name)
