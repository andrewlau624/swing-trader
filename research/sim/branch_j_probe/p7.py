from research.sim.borrow_xs import conn
import pandas as pd
db=conn()
# placebo: non-ex nights CO for ZA/SE pref quotes
for r in ['ZA','SE']:
    d=db.raw_sql(f"select infocode from tr_ds_equities.ds2ctryqtinfo where region='{r}' and typecode='PREF'")
    ch=",".join(str(int(x)) for x in d.infocode)
    p=db.raw_sql(f"select infocode,marketdate,open_,close_ from tr_ds_equities.ds2primqtprc where infocode in ({ch}) and marketdate>='2015-01-01' and close_>0 and open_>0")
    p=p.sort_values(['infocode','marketdate']);p['pc']=p.groupby('infocode').close_.shift(1);p['co']=p.open_/p.pc-1
    print(r,'all-nights CO mean(bp) clip',p.co.clip(-.05,.05).mean()*1e4,'median',p.co.median()*1e4,'open==pc share',(p.open_==p.pc).mean())
