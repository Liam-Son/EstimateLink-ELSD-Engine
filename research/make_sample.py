"""Deterministic fake point-in-time-like panel for plumbing tests only."""
import argparse,csv,datetime as dt,math
from pathlib import Path
COLUMNS=("date ticker sector industry open high low close volume adv20 est_ptp est_fcf est_eps earnings_certainty_rank_derivative implied_volatility_call_180 implied_volatility_put_180").split()
def make_sample(output,names=80,days=320,with_gaps=False):
    output.parent.mkdir(parents=True,exist_ok=True);volhist={i:[] for i in range(names)}
    with output.open("w",newline="") as f:
        w=csv.writer(f);w.writerow(COLUMNS);date=dt.date(2023,1,2);t=0
        while t<days:
            if date.weekday()<5:
                for i in range(names):
                    if with_gaps and i==0 and 120<=t<=122:continue
                    base=40+i*.35+.02*t+math.sin(t*.11+i*.3);o=base+math.sin(t*.3+i)*.15;c=base+math.cos(t*.23+i*.7)*.18
                    hi=max(o,c)+.3;lo=min(o,c)-.3;vol=100000+i*700+int(10000*math.sin(t*.13+i));volhist[i].append(vol)
                    adv=sum(volhist[i][-20:])/20 if len(volhist[i])>=20 else ""
                    # deterministic sparse estimate/IV missingness to exercise backfill
                    ptp="" if (t+i)%47==0 else 1+.15*math.sin(t*.08+i)
                    fcf="" if (t+2*i)%53==0 else 2+.1*math.cos(t*.09+i*.7)
                    eps="" if (t+3*i)%59==0 else .7+.12*math.sin(t*.07+i*.2)
                    ivc="" if (t+i)%61==0 else .25+.04*math.sin(t*.04+i)
                    ivp="" if (t+2*i)%67==0 else .28+.03*math.cos(t*.06+i)
                    w.writerow([date.isoformat(),f"T{i:03d}",f"S{i%8}",f"I{i%24}",o,hi,lo,c,vol,adv,ptp,fcf,eps,.5+.3*math.cos(t*.05+i),ivc,ivp])
                t+=1
            date+=dt.timedelta(days=1)
    print(f"Wrote synthetic plumbing panel: {output}")
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,default=Path("sample.csv"));ap.add_argument("--names",type=int,default=80);ap.add_argument("--days",type=int,default=320);ap.add_argument("--with-gaps",action="store_true")
    a=ap.parse_args();make_sample(a.output,a.names,a.days,a.with_gaps)
