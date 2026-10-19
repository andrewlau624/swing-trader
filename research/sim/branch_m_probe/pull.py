import pandas as pd, time
from research.sim.borrow_xs import conn
db=conn(); OUT='/private/tmp/claude-501/-Users-andrewlau-Documents-Code-Projects-swing-trader/bad619c6-1952-49ad-9cea-d66d4400c09e/scratchpad/m/'
import os; os.makedirs(OUT,exist_ok=True)
q=db.raw_sql("select infocode,dsqtname,delistdate from tr_ds_equities.ds2ctryqtinfo where region='JP' and typecode='EQ' and isprimqt=1 and primisocurrcode='JPY'")
q.to_parquet(OUT+'q.parquet'); ics=q.infocode.astype(int).tolist(); print(len(ics))
dv=[];px=[];t=time.time()
for i in range(0,len(ics),250):
    ch=",".join(map(str,ics[i:i+250]))
    px.append(db.raw_sql(f"select infocode,marketdate,open_,close_,volume from tr_ds_equities.ds2primqtprc where infocode in ({ch}) and marketdate>='2004-12-01' and close_>0"))
    dv.append(db.raw_sql(f"select infocode,divtypecode,divrate,effectivedate,effdateestflag,isocurrcode from tr_ds_equities.ds2div where infocode in ({ch}) and effectivedate>='2005-01-01' and divrate>0"))
    print(i,time.time()-t,flush=True)
pd.concat(px).to_parquet(OUT+'px.parquet'); pd.concat(dv).to_parquet(OUT+'dv.parquet')
