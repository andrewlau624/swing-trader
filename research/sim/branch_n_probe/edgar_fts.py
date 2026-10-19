import requests, sys, json, time
UA={"User-Agent":"research andrewlau2007@gmail.com"}
def q(text, a, b, forms=None):
    p={"q":text,"dateRange":"custom","startdt":a,"enddt":b}
    if forms: p["forms"]=forms
    r=requests.get("https://efts.sec.gov/LATEST/search-index",params=p,headers=UA,timeout=30).json()
    print("##",text,a,b,forms,"total",r["hits"]["total"]["value"])
    for h in r["hits"]["hits"][:15]:
        s=h["_source"]; print(s["file_date"],s["form"],"|",s["display_names"][0][:70],"|",h["_id"])
    time.sleep(.5)
for args in [
 ('"mandatory redemption" "asset coverage" "cure"',"2020-03-01","2020-09-30","8-K"),
 ('"failure to maintain" "asset coverage" "redeem" "preferred"',"2020-03-01","2020-09-30","8-K"),
 ('"asset coverage" "preferred" "below 200%"',"2008-09-01","2009-06-30",None),
 ('"asset coverage" "preferred" "below 200%"',"2022-06-01","2023-06-30",None),
 ('"mandatory redemption" "asset coverage" "preferred shares"',"2022-06-01","2023-06-30","8-K"),
]: q(*args)
print("=========== part 2")
for args in [
 ('"Oxford Lane" "asset coverage" preferred',"2020-04-01","2020-08-31","N-CSR"),
 ('"Priority Income Fund" "asset coverage"',"2020-03-01","2020-09-30",None),
 ('"OFS Credit" "asset coverage"',"2020-03-01","2020-09-30",None),
 ('"Eagle Point Credit" "asset coverage"',"2020-03-01","2020-09-30",None),
]: q(*args)
