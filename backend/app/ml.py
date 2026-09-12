from pathlib import Path
from datetime import datetime
import json, random, time
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy.orm import Session
from .models import TrainingRun, Metric, Checkpoint, Dataset
from .core import settings, CPU_COUNT

class MLP(nn.Module):
    def __init__(self, input_size, output_size, hidden, activation='relu', dropout=0.0):
        super().__init__()
        acts={'relu':nn.ReLU,'tanh':nn.Tanh,'gelu':nn.GELU}
        layers=[]; prev=input_size
        for h in hidden:
            if h < 1: raise ValueError('Hidden layer sizes must be positive')
            layers += [nn.Linear(prev,h), acts.get(activation,nn.ReLU)()]
            if dropout: layers.append(nn.Dropout(dropout))
            prev=h
        layers.append(nn.Linear(prev,output_size)); self.net=nn.Sequential(*layers)
    def forward(self,x): return self.net(x)

def set_seed(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)

def load_tabular(path: Path, target: str):
    ext=path.suffix.lower()
    if ext=='.csv': df=pd.read_csv(path)
    elif ext=='.json': df=pd.read_json(path)
    elif ext=='.jsonl': df=pd.read_json(path,lines=True)
    else: raise ValueError('Supported tabular formats: CSV, JSON, JSONL')
    if df.empty: raise ValueError('Dataset is empty')
    if target not in df.columns: raise ValueError(f'Target column {target!r} does not exist')
    df=df.drop_duplicates().copy(); y=df.pop(target)
    X=pd.get_dummies(df,dummy_na=True).replace([np.inf,-np.inf],np.nan)
    if X.isna().any().any(): X=X.fillna(X.median(numeric_only=True)).fillna(0)
    if y.isna().any(): raise ValueError('Target contains missing values')
    return X.astype('float32'), y

def prepare_splits(X,y,task,seed,ratios):
    tr,va,te=ratios
    if min(ratios)<=0 or abs(tr+va+te-1)>1e-6: raise ValueError('Split ratios must be > 0 and sum to 1')
    strat=y if task=='classification' and y.nunique()>1 else None
    Xtr,Xtmp,ytr,ytmp=train_test_split(X,y,test_size=1-tr,random_state=seed,stratify=strat)
    rel_te=te/(va+te); strat2=ytmp if task=='classification' and ytmp.nunique()>1 else None
    Xva,Xte,yva,yte=train_test_split(Xtmp,ytmp,test_size=rel_te,random_state=seed,stratify=strat2)
    scaler=StandardScaler().fit(Xtr)
    return [(scaler.transform(z).astype('float32'),a.reset_index(drop=True)) for z,a in [(Xtr,ytr),(Xva,yva),(Xte,yte)]]

def make_targets(ytr,yva,yte,task):
    if task=='regression': return [torch.tensor(np.asarray(y,dtype='float32')).view(-1,1) for y in (ytr,yva,yte)],1
    labels=sorted(pd.unique(pd.concat([ytr,yva,yte])).tolist(),key=str); mp={v:i for i,v in enumerate(labels)}
    return [torch.tensor([mp[v] for v in y],dtype=torch.long) for y in (ytr,yva,yte)],len(labels)

def evaluate(model,loader,loss_fn,task):
    model.eval(); losses=[]; ys=[]; ps=[]
    with torch.no_grad():
        for xb,yb in loader:
            out=model(xb); loss=loss_fn(out,yb); losses.append(loss.item()*len(yb)); ys.extend(yb.numpy().tolist()); ps.extend(out.numpy().tolist())
    loss=sum(losses)/len(ys)
    if task=='regression':
        pred=np.asarray(ps).reshape(-1); true=np.asarray(ys)
        return loss,{'mae':float(mean_absolute_error(true,pred)),'rmse':float(mean_squared_error(true,pred)**0.5),'r2':float(r2_score(true,pred))}
    pred=np.argmax(np.asarray(ps),axis=1); p,r,f,_=precision_recall_fscore_support(ys,pred,average='weighted',zero_division=0)
    return loss,{'accuracy':float(accuracy_score(ys,pred)),'precision':float(p),'recall':float(r),'f1':float(f)}

def train_run(db:Session,run_id:str):
    run=db.get(TrainingRun,run_id); run.status='PREPARING'; db.commit()
    try:
        cfg=run.config; set_seed(int(cfg['seed']))
        workers=max(0,min(CPU_COUNT,int(cfg['cpu_workers']))); threads=max(1,min(CPU_COUNT,int(cfg['threads'])))
        torch.set_num_threads(threads)
        dataset=db.get(Dataset,run.dataset_id); X,y=load_tabular(Path(dataset.path),cfg['target'])
        (Xtr,ytr),(Xva,yva),(Xte,yte)=prepare_splits(X,y,cfg['task'],cfg['seed'],(cfg['train_ratio'],cfg['val_ratio'],cfg['test_ratio']))
        targets,out=make_targets(ytr,yva,yte,cfg['task']); model=MLP(Xtr.shape[1],out,cfg['hidden_layers'],cfg['activation'],cfg['dropout'])
        loss_fn=nn.MSELoss() if cfg['task']=='regression' else nn.CrossEntropyLoss(); opt_cls={'adam':torch.optim.Adam,'sgd':torch.optim.SGD}[cfg['optimizer']]
        opt=opt_cls(model.parameters(),lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
        train_loader=DataLoader(TensorDataset(torch.tensor(Xtr),targets[0]),batch_size=cfg['batch_size'],shuffle=True,num_workers=workers)
        val_loader=DataLoader(TensorDataset(torch.tensor(Xva),targets[1]),batch_size=cfg['batch_size'],shuffle=False,num_workers=workers)
        test_loader=DataLoader(TensorDataset(torch.tensor(Xte),targets[2]),batch_size=cfg['batch_size'],shuffle=False,num_workers=workers)
        run.status='RUNNING'; run.started_at=datetime.utcnow(); db.commit(); run_dir=settings.storage_root/'runs'/run_id; run_dir.mkdir(parents=True,exist_ok=True); best=float('inf')
        for epoch in range(1,cfg['epochs']+1):
            if (run_dir/'cancel').exists(): run.status='CANCELLED'; run.finished_at=datetime.utcnow(); db.commit(); return
            while (run_dir/'pause').exists(): run.status='PAUSED'; db.commit(); time.sleep(0.5)
            run.status='RUNNING'; db.commit(); model.train(); t0=time.time(); total=n=0
            for xb,yb in train_loader:
                opt.zero_grad(set_to_none=True); outp=model(xb); loss=loss_fn(outp,yb); loss.backward(); opt.step(); total+=loss.item()*len(yb); n+=len(yb)
            tl=total/n; vl,vm=evaluate(model,val_loader,loss_fn,cfg['task']); elapsed=max(time.time()-t0,1e-6)
            tm=evaluate(model,train_loader,loss_fn,cfg['task'])[1]; metric_key='accuracy' if cfg['task']=='classification' else 'r2'
            for split,lossv,m in [('train',tl,tm),('validation',vl,vm)]: db.add(Metric(run_id=run_id,epoch=epoch,split=split,loss=lossv,metric=m[metric_key],learning_rate=opt.param_groups[0]['lr'],samples_per_sec=n/elapsed))
            ck=run_dir/f'checkpoint-{epoch}.pt'; torch.save({'model_state':model.state_dict(),'optimizer_state':opt.state_dict(),'epoch':epoch,'config':cfg,'seed':cfg['seed'],'input_size':Xtr.shape[1],'output_size':out},ck)
            db.add(Checkpoint(run_id=run_id,epoch=epoch,path=str(ck),is_best=vl<best)); best=min(best,vl); db.commit()
        test_loss,test_metrics=evaluate(model,test_loader,loss_fn,cfg['task']); (run_dir/'test_metrics.json').write_text(json.dumps({'loss':test_loss,**test_metrics},indent=2))
        run.status='COMPLETED'; run.finished_at=datetime.utcnow(); db.commit()
    except Exception as exc:
        run.status='FAILED'; run.error=f'{type(exc).__name__}: {exc}'; run.finished_at=datetime.utcnow(); db.commit(); raise
