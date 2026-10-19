import time
from research.sim.borrow_xs import conn
db=conn()
t=time.time()
print(db.raw_sql("select * from tr_ds_equities.ds2div limit 2").T)
print(db.raw_sql("select divtypecode,count(*) from tr_ds_equities.ds2div d join tr_ds_equities.ds2ctryqtinfo c using(infocode) where c.region='JP' and effectivedate>='2005-01-01' group by 1").to_string())
print(db.raw_sql("select * from tr_ds_equities.ds2mktval limit 2").T)
print(db.raw_sql("select * from tr_ds_equities.ds2sharehldgs limit 2").T)
print(time.time()-t)
