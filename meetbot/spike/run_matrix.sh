#!/usr/bin/env bash
# Full go/no-go matrix. Each cell gets its own Chrome on its own debug port.
# Port 9222 (tln-browser.service) is never touched.
set -u
cd "$(dirname "$0")"
mkdir -p results
PORT=9340
REPS="${REPS:-2}"

for rep in $(seq 1 "$REPS"); do
  for mode in headless-new headless-old xvfb; do
    for ap in noautoplay autoplay; do
      flag=""
      [ "$ap" = "autoplay" ] && flag="--autoplay"
      name="${mode}_${ap}_rep${rep}"
      echo "=== $name (port $PORT) ==="
      timeout 180 node run_probe.mjs --port "$PORT" --mode "$mode" $flag \
        > "results/${name}.json" 2>"results/${name}.stage"
      node -e '
        const fs=require("fs");
        const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));
        const v=j.verdicts||{};
        const m=j.results&&j.results.mediaElement||{};
        const w=j.results&&j.results.worklet||{};
        console.log("  osc=%s  mediaElement=%s  worklet=%s",v.oscillator,v.mediaElement,v.worklet);
        console.log("  ctxState=%s play=%s clockStartMs=%s peak=%s dom=%sHz",
          m.ctxStateAfterResume, m.playError?("BLOCKED("+m.playError.split(":")[0]+")"):"ok",
          m.clockStartMs, (m.peakAbs||0).toFixed(4), m.dominantHz&&m.dominantHz.toFixed(0));
        console.log("  worklet quanta=%s nonZero=%s frames=%s peak=%s",
          w.quanta,w.nonZeroQuanta,w.framesSeen,(w.peakAbs||0).toFixed(4));
      ' "results/${name}.json" 2>/dev/null || echo "  (probe failed, see results/${name}.json)"
      PORT=$((PORT+1))
    done
  done
done
echo "done. raw json in $(pwd)/results/"
