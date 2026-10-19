import requests,re,html
UA={"User-Agent":"research andrewlau2007@gmail.com"}
docs={'OXLC N-CSR FY3/2020':('1495222','000161577420005611','s124917_ncsr.htm'),
 'OCCI N-CSRS 4/30/2020':('1716951','000171695120000026','occin-csr4302020.htm'),
 'PRIF N-CSR 6/2020':('1554625','000155462520000089','pris2020q4n-csr.htm'),
 'ECC N-CSRS 6/2020':('1604174','000110465920095774','tm2027422d1_ncsrs.htm')}
for k,(cik,acc,fn) in docs.items():
    r=requests.get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{fn}",headers=UA,timeout=60)
    t=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',r.text)))
    print('\n=====',k,r.status_code,len(t))
    ms=[m for m in re.finditer(r'asset coverage',t,re.I)]
    seen=0
    for m in ms:
        s=t[max(0,m.start()-120):m.end()+260]
        if re.search(r'\d{3}(\.\d)?\s?%|per unit|\$\s?\d',s):
            print('..',s); seen+=1
        if seen>=4: break
