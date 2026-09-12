import numpy as np
import pandas as pd
import torch
from app.ml import MLP, prepare_splits, make_targets

def test_model_weights_change_after_real_backward():
    torch.manual_seed(7); m=MLP(3,2,[8]); before=[p.detach().clone() for p in m.parameters()]
    x=torch.randn(12,3); y=torch.randint(0,2,(12,)); opt=torch.optim.SGD(m.parameters(),lr=0.1)
    loss=torch.nn.CrossEntropyLoss()(m(x),y); loss.backward(); opt.step()
    assert loss.item()>0 and any(not torch.equal(a,b) for a,b in zip(before,m.parameters()))

def test_reproducible_split():
    X=pd.DataFrame(np.arange(200).reshape(100,2),columns=['a','b']); y=pd.Series([0,1]*50)
    a=prepare_splits(X,y,'classification',42,(.7,.15,.15))[0]; b=prepare_splits(X,y,'classification',42,(.7,.15,.15))[0]
    assert np.array_equal(a[0][0],b[0][0]); targets,n,_=make_targets(a[0][1],a[1][1],a[2][1],'classification')
    assert n==2 and targets[0].dtype==torch.long
