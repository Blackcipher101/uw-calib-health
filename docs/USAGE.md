# How to run and tests (details)

[Back to README](../README.md)

## How to run
Environment: a Python venv with numpy 2.5, cv2 5.0, rosbags 0.11.7, ruamel; no scipy). The estimator itself needs only numpy + OpenCV (+ PyYAML or ruamel); `rosbags` only for bag reading.
```
cd calib_health
PY=python3   # venv with numpy, opencv-python, rosbags, PyYAML
export UWB_DATA=~/svin_data   # dataset root: ntnu/{traj_06/traj_06_ros2,calibration}, bus_outside/; UWB_MOCAP for validate_gt.py
$PY extract_cache.py ntnu 105 60          # tracks -> cache/ (2-3 MB per stretch)
$PY baseline.py --boot 30 | tee results/results_baseline.log   # experiment A (~18 min), then: $PY summarize.py
$PY warp_study.py 105,170                  # experiment B (~3 min)
$PY window_study.py && $PY summarize_window.py   # experiment C
$PY run_bus.py 100,250,400 60              # experiment D
$PY make_figures.py --cache cache          # regenerate docs/figures/*.png (fig4 needs cache/ntnu_105_60_k6g6.npz and UWB_DATA)
$PY validate_gt.py 40 60                   # mocap-scale oracle (not part of the tool)
python3 -m pytest -q tests                 # synthetic tests, 13 tests, ~1.5 s, no bag needed
```
Programmatic use: `prep = estimators.prepare(rig, stretch); r = estimators.estimate(prep, rig); estimators.verdict(rig, r.fused_deg)`.
`estimate` needs n_boot >= 1 (the fusion weights come from the bootstrap).

## Tests (`tests/test_synthetic.py`)
Synthetic fisheye stereo scene (ranges 1.2-6 m, random camera motion, 0.2 px noise) with injected rotations: static fit recovers x and z (+-0.03 deg),
static fit recovers y via the x'y' term (+-0.08), motion intercept recovers y (+-0.12), full estimate + verdict (0 -> OK, 0.5 deg about y -> RECALIBRATE),
inject round trip, threshold arithmetic. A mutation (basis-column to axis mapping bug that occurred during development) makes 6 of 13 tests fail.
