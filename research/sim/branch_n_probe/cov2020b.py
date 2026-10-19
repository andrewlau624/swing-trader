import requests,re,html
UA={"User-Agent":"research andrewlau2007@gmail.com"}
docs={'OXLC':('1495222','000161577420005611','s124917_ncsr.htm',r'(Asset Coverage|asset coverage) (per|ratio|of)'),
 'ECC':('1604174','000110465920095774','tm2027422d1_ncsrs.htm',r'(Asset Coverage|asset coverage) (per|ratio|of|for)'),
 'PRIF':('1554625','000155462520000089','pris2020q4n-csr.htm',r'(Asset Coverage|asset coverage) (per|ratio|of|for)')}
for k,(cik,acc,fn,pat) in docs.items():
    t=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',requests.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{fn}",headers=UA).text)))
    print('\n==',k)
    n=0
    for m in re.finditer(pat,t):
        s=t[m.start()-50:m.end()+380]
        if re.search(r'\d,\d{3}|\d{3}\.\d+%|\b\d{3}%',s) and 'at least 200%' not in s[:150]:
            print('..',s);n+=1
        if n>=3:break
