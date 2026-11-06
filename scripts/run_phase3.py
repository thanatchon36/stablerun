import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from stablerun.config import load_config, ROOT
from stablerun.experiments2 import run_e3, run_e4, run_e5, run_benchmark
cfg = load_config(); out = ROOT / "results"
t0 = time.time()
run_e4(cfg, out); print(f"E4 done {time.time()-t0:.0f}s", flush=True)
run_benchmark(cfg, out); print(f"benchmark done {time.time()-t0:.0f}s", flush=True)
run_e5(cfg, out); print(f"E5 done {time.time()-t0:.0f}s", flush=True)
run_e3(cfg, out); print(f"E3 done {time.time()-t0:.0f}s", flush=True)
print("ALL DONE", flush=True)
