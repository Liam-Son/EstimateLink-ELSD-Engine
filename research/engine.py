"""Estimate-Link × Certainty × IV180 Sector Hybrid v3.0 research-hardened engine."""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
from data_layer import load_panel,write_quality,sha256_file
from signal_engine import compute
from backtest import run_strategy,yearly_metrics,split_metrics,ic_report,block_bootstrap,cost_stress
from portfolio import weights
from operators import ok,NAN

ROOT=Path(__file__).resolve().parent

def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _hash_json(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def write_signals(output,days,signals,components,cfg):
    pc=cfg["portfolio"]
    with (output/"signals.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["date","ticker","raw_signal","target_weight"])
        for d in days:
            ww=weights(signals[d],cap=pc["max_abs_weight"],gross_target=pc["gross_target"])
            if len([x for x in ww.values() if abs(x)>0])<pc["min_names"]:ww={}
            for k,v in sorted(signals[d].items()):
                if ok(v):w.writerow([d,k,v,ww.get(k,0.0)])
    cols=["date","ticker","stable","link_alpha","certainty","iv180","core","core_decay4","range_decay5","rng",
          "pre_platform_decay","final_signal","adv20_used","estimate_max_age_obs","iv_age_obs"]
    with (output/"components.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(cols)
        for d in days:
            for k,c in sorted(components[d].items()):w.writerow([d,k]+[c.get(x,NAN) for x in cols[2:]])

def component_signals(components,field):
    return {d:{k:c.get(field,NAN) for k,c in rows.items()} for d,rows in components.items()}

def run(source,output,config_path,cost_bps=None,adv20_mode=None,gap_policy=None,price_policy=None,os_start=None,strict=True):
    cfg=load_config(config_path); rc=cfg["research"]
    alpha_source_name=cfg.get("brain_alpha_source","brain_alpha.json")
    if Path(alpha_source_name).name != alpha_source_name:
        raise ValueError("brain_alpha_source must name a file in the research directory")
    alpha_source=ROOT/alpha_source_name
    if not alpha_source.is_file():
        raise FileNotFoundError(alpha_source)
    adv20_mode=adv20_mode or rc["adv20_mode"];gap_policy=gap_policy or rc["gap_policy"];price_policy=price_policy or rc["price_policy"]
    dates,quality=load_panel(source,strict=strict)
    signals,components,sigdiag=compute(dates,cfg,adv20_mode=adv20_mode,gap_policy=gap_policy,include_components=True)
    output.mkdir(parents=True,exist_ok=True);days=sorted(dates)
    write_signals(output,days,signals,components,cfg)
    bt_rows,metrics=run_strategy(dates,signals,cfg,cost_bps=cost_bps,price_policy=price_policy,output_csv=output/"backtest.csv")
    code_hashes={name:sha256_file(ROOT/name) for name in ("engine.py","operators.py","data_layer.py","signal_engine.py","portfolio.py","backtest.py","ibkr_paper.py")}
    report={
        "engine_version":"3.0","alpha_id":cfg["alpha_id"],"alpha_name":cfg["alpha_name"],"metrics":metrics,
        "yearly":yearly_metrics(bt_rows),"is_os":split_metrics(bt_rows,os_start),"ic":ic_report(dates,signals,cfg["timing"]["delay_days"]),
        "bootstrap":block_bootstrap(bt_rows),"cost_stress":cost_stress(dates,signals,cfg),
        "signal_diagnostics":sigdiag,"input_sha256":quality["input_sha256"],"config_sha256":_hash_json(cfg),
        "brain_alpha_source":alpha_source_name,"brain_alpha_sha256":sha256_file(alpha_source),"code_sha256":code_hashes,
        "warning":"Offline BRAIN approximation. No synthetic or offline result is evidence of future performance. Exact proprietary BRAIN semantics are not claimed."
    }
    (output/"report.json").write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")

    # Attribution/ablation without retuning parameters.
    ab={}
    for label,field in [("link","link_alpha"),("certainty","certainty"),("iv180","iv180"),("core","core"),("range","rng"),("pre_platform_decay","pre_platform_decay"),("final","final_signal")]:
        ss=component_signals(components,field)
        try:
            rows,m=run_strategy(dates,ss,cfg,cost_bps=cost_bps,price_policy=price_policy)
            ab[label]={"metrics":m,"ic":ic_report(dates,ss,cfg["timing"]["delay_days"])}
        except ValueError as e:
            ab[label]={"error":str(e)}
    (output/"ablation.json").write_text(json.dumps(ab,indent=2,sort_keys=True),encoding="utf-8")
    write_quality(output/"data_quality.json",quality,{"signal_diagnostics":sigdiag,"adv20_mode":adv20_mode,"gap_policy":gap_policy})
    (output/"run_manifest.json").write_text(json.dumps({
        "engine_version":"3.0","input":str(source),"input_sha256":quality["input_sha256"],"config_sha256":_hash_json(cfg),
        "brain_alpha_source":alpha_source_name,"brain_alpha_sha256":sha256_file(alpha_source),"code_sha256":code_hashes,"strict_validation":strict,"adv20_mode":adv20_mode,
        "gap_policy":gap_policy,"price_policy":price_policy,"os_start":os_start,
    },indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(report,indent=2,sort_keys=True))
    return report

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",required=True,type=Path);ap.add_argument("--output",type=Path,default=Path("output"))
    ap.add_argument("--config",type=Path,default=ROOT/"config.json");ap.add_argument("--cost-bps",type=float,default=None)
    ap.add_argument("--adv20-mode",choices=("auto","input","rolling"),default=None)
    ap.add_argument("--gap-policy",choices=("reset","compress"),default=None)
    ap.add_argument("--price-policy",choices=("error","drop"),default=None)
    ap.add_argument("--os-start",default=None,help="YYYY-MM-DD; produces descriptive IS/OS split without tuning")
    ap.add_argument("--non-strict-input",action="store_true")
    a=ap.parse_args()
    if a.cost_bps is not None and a.cost_bps<0:ap.error("cost-bps must be >=0")
    if a.os_start:
        import datetime as _dt
        try:_dt.date.fromisoformat(a.os_start)
        except ValueError:ap.error("os-start must be YYYY-MM-DD")
    run(a.input,a.output,a.config,a.cost_bps,a.adv20_mode,a.gap_policy,a.price_policy,a.os_start,not a.non_strict_input)
