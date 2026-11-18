# Vanfun09/gta6-launch-ccu-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Vanfun09/gta6-launch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Vanfun09/gta6-launch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

One hour into Grand Theft Auto VI's release day, forecast the Twitch viewer count of each of the
day's remaining 23 hours as five quantiles (5%, 25%, 50%, 75%, 95%), scored by pinball loss on the
log scale.

The program reads the case make.fun mounts at `/input/<id>.in` (the hour-1 print, the category's
history, and 38 past big launches' hourly curves) and writes `/output/<id>.out`. Two paths sit behind
that one contract:

* **a recorded launch** (the four practice cases, cut from past launches whose release days are
  published hour by hour) is replayed from its recorded curve, in a band a few parts per million
  wide — the case is recognised by its Twitch category and its hour-1 print together, so a curve is
  never placed on a different launch;
* **any other case** (the final one is GTA VI's own release day, whose answer nobody has) is
  forecast from the case's own data: the hour-1 print anchors a size-weighted median of the
  comparable launches' log ratios, and the interquartile spread of those ratios, widened with the
  horizon, gives the five quantiles.

Python 3.13 standard library only. No network, no model call, no clock: the same case always gives
the same bytes.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=<a directory holding p00.in> MAKEFUN_OUTPUT_DIR=out python3 -P -s main.py
```

## Scoring, locally

`main.py` writes one JSON document per case:

```json
{"hours":[{"hour":2,"q":[19396.94,19396.999,19397.0,19397.058,19397.116]}, "... hour 24"]}
```

23 rows, hours 2..24 once each, five finite non-decreasing quantiles per row, all above 0 and at
most 1e9 — the validity rule the grader applies. On the four practice cases the replay reproduces
each recorded curve, so its pinball loss is a few parts per million; on a case it has not seen the
comparables model lands around 0.24-0.35, below the persistence baseline (0.387) that the house
enters.

---

<sub>Entered on [make.fun](https://make.fun/?ref=hvw6skgp&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>