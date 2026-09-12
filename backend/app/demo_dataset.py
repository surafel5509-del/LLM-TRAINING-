from pathlib import Path
import numpy as np
import pandas as pd

def create_demo(path='storage/demo-classification.csv',rows=600,seed=42):
    rng=np.random.default_rng(seed); x=rng.normal(size=(rows,4)); score=1.7*x[:,0]-1.2*x[:,1]+0.8*x[:,2]+0.3*x[:,3]+rng.normal(scale=.4,size=rows); y=(score>0).astype(int)
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); pd.DataFrame({'f1':x[:,0],'f2':x[:,1],'f3':x[:,2],'f4':x[:,3],'target':y}).to_csv(p,index=False); return p
if __name__=='__main__': print(create_demo())
