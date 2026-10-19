from research.sim.borrow_xs import conn
db=conn()
print(db.raw_sql("select * from tr_ds_equities.ds2ctryqtinfo where region='JP' limit 3").T)
print(db.raw_sql("select typecode,count(*) from tr_ds_equities.ds2ctryqtinfo where region='JP' group by 1").to_string())
q=db.raw_sql("select infocode from tr_ds_equities.ds2ctryqtinfo where region='JP' and typecode='EQ' limit 3")
print(q)
print(db.raw_sql("select table_name from information_schema.tables where table_schema='tr_ds_equities'").table_name.tolist())
