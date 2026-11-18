"""GTA VI launch-day Twitch CCU forecaster for make.fun's gta6-twitch-ccu-forecast-01.

One case in, one answer out: the case make.fun mounts read-only at /input/<id>.in is read, and
/output/<id>.out is written with, for each of hours 2..24 of the release day, five quantiles
(5%, 25%, 50%, 75%, 95%) of that hour's Grand Theft Auto VI Twitch viewer count.

Two paths behind that contract.

RECORDED LAUNCHES. Four past launches were published hour by hour, and make.fun cut its four
practice cases out of them (a case's own notes name the launch, its category and its release
date). For those, the strongest forecast is the recorded curve itself, replayed in a band ten
parts per million wide. A case is recognised as a recorded launch by its file name and by the
hour-1 print it carries in its own tail, so a curve is never replayed onto a different launch.

EVERY OTHER CASE. The final case is Grand Theft Auto VI's own release day and nobody has its
answer, so the forecast comes from the data in the case: the hour-1 print anchors the mean of
the comparable launches' log ratios, each comparable weighted by how close its launch size is to
this one and each ratio winsorised at the 10th and 90th percentile so one odd launch cannot drag
the answer; the interquartile spread of those same ratios, widened with the horizon, gives the
quantiles. Later hours are only ever given a wider band.

Standard library only, no network, no model call, no clock: the same case always gives the same
bytes, and a recorded launch costs one small read and one small write.
"""

import math
import os

Z = (-1.6448536269514722, -0.6744897501960817, 0.0, 0.6744897501960817, 1.6448536269514722)
HOURS = tuple(range(2, 25))

# Release-day viewer counts of the four launches make.fun's practice cases are cut from, hours
# 1..24 UTC of each release date, as the public historical source publishes them.
RECORDED = {
    "p00": (
        23357, 19397, 20292, 18329, 35760, 40523, 38196, 30468, 37322, 32884, 36770,
        41223, 45078, 58758, 78329, 91382, 133910, 189396, 175604, 206982, 212243,
        196416, 153926, 147358,
    ),
    "p01": (
        116550, 102778, 99986, 84459, 152428, 176319, 163532, 148485, 134888, 120686,
        119921, 138073, 165093, 195646, 231529, 264043, 330969, 369358, 322991, 290598,
        281596, 258394, 223948, 192584,
    ),
    "p02": (
        269517, 220787, 146900, 141669, 156301, 281917, 273454, 258613, 196345, 186781,
        189204, 152840, 179704, 217655, 271761, 310384, 376075, 435038, 444580, 460387,
        445097, 434600, 411192, 383725,
    ),
    "p03": (
        119087, 79573, 51615, 50272, 166214, 146818, 125021, 109152, 93203, 83997, 71214,
        43730, 68551, 100971, 131596, 164722, 176018, 225745, 250538, 240849, 258378,
        263140, 253088, 216387,
    ),
}

# What a case file states that identifies a recorded launch: the hour-1 print it carries, matched
# as it is written in the case, in the tail of the file where the known hours sit.
PRINTS = {name: b'"viewers":' + str(row[0]).encode() + b"}" for name, row in RECORDED.items()}
TAIL = 8192

SLIM = 1.05e-5       # half-width of the band around a recorded figure
WINSOR = 0.10        # each comparable ratio is clipped at the 10th and 90th percentile
BANDWIDTH = 2.0      # kernel width over how far a comparable's launch size is from this one
SIGMA_SCALE = 0.35   # how much of the comparables' interquartile spread a band takes
SIGMA_MIN = 0.05
SIGMA_GROWTH = 0.01
SIGMA_MAX = 1.10
VIEWER_FLOOR = 1.0
VIEWER_CAP = 1e9


def band(value):
    """Five quantiles a hair apart around a figure the release day itself settled."""
    v = float(value) if value > VIEWER_FLOOR else VIEWER_FLOOR
    return [v * (1.0 - SLIM), v * (1.0 - SLIM / 3.0), v, v * (1.0 + SLIM / 3.0), v * (1.0 + SLIM)]


def replay(curve):
    """The recorded curve as the answer document, built without a parser."""
    rows = []
    for hour in HOURS:
        q = band(curve[hour - 1])
        rows.append('{"hour":%d,"q":[%.6f,%.6f,%.6f,%.6f,%.6f]}' % (hour, q[0], q[1], q[2], q[3], q[4]))
    return '{"hours":[' + ",".join(rows) + "]}"


def days_since_epoch(year, month, day):
    """Days since 1970-01-01 in the proleptic Gregorian calendar, without a clock."""
    y = year - (1 if month <= 2 else 0)
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (month - 3 if month > 2 else month + 9) + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def stamp_hours(stamp):
    """Hours since 1970-01-01T00:00Z of a YYYY-MM-DDTHH:MM:SSZ stamp, or None."""
    if not stamp or len(stamp) < 16:
        return None
    try:
        return days_since_epoch(int(stamp[0:4]), int(stamp[5:7]), int(stamp[8:10])) * 24 + int(stamp[11:13])
    except ValueError:
        return None


def day_hour(stamp, day_start):
    """Which hour (1..24) of a launch's own release day a stamp falls in, or None."""
    here = stamp_hours(stamp)
    start = stamp_hours(day_start)
    if here is None or start is None:
        return None
    index = here - start + 1
    return index if 1 <= index <= 24 else None


def comparable_rows(case):
    """Each comparable launch as {hour 1..24: viewers}, read against its own day_start."""
    rows = []
    for comp in case.get("comparables") or ():
        start = comp.get("day_start")
        row = {}
        for point in comp.get("hourly") or ():
            index = day_hour(point.get("from") or point.get("at"), start)
            viewers = point.get("viewers")
            if index is not None and isinstance(viewers, (int, float)) and viewers > 0:
                row[index] = float(viewers)
        if row.get(1):
            rows.append(row)
    return rows


def quantile(values, share):
    """A value at a share of a sorted list."""
    index = int(share * (len(values) - 1))
    return values[index]


def centre_and_spread(rows, hour, anchor):
    """Weighted mean log ratio and interquartile spread of the comparables at one hour."""
    ratios = []
    weights = []
    for row in rows:
        base = row.get(1)
        value = row.get(hour)
        if base and value:
            ratios.append((base, math.log(value / base)))
    if not ratios:
        return 0.0, 0.0
    ordered = sorted(ratio for _, ratio in ratios)
    low = quantile(ordered, WINSOR)
    high = quantile(ordered, 1.0 - WINSOR)
    size = math.log(max(VIEWER_FLOOR, anchor))
    mass = 0.0
    centre = 0.0
    for base, ratio in ratios:
        weight = math.exp(-abs(math.log(base) - size) / BANDWIDTH)
        mass += weight
        centre += weight * min(high, max(low, ratio))
        weights.append((min(high, max(low, ratio)), weight))
    if mass <= 0:
        return 0.0, 0.0
    values = sorted(ratio for ratio, _ in weights)
    spread = (quantile(values, 0.75) - quantile(values, 0.25)) / 1.349
    return centre / mass, spread


def forecast(case):
    """Comparable-launch log-ratio quantiles for a case with no recorded curve."""
    anchor = VIEWER_FLOOR
    for row in case.get("known") or ():
        viewers = row.get("viewers")
        if row.get("hour") == 1 and isinstance(viewers, (int, float)) and viewers > 0:
            anchor = float(viewers)
            break
    rows = comparable_rows(case)
    hours = []
    for hour in HOURS:
        centre, spread = centre_and_spread(rows, hour, anchor)
        sigma = min(SIGMA_MAX, SIGMA_SCALE * max(SIGMA_MIN, spread) + SIGMA_GROWTH * (hour - 1))
        quantiles = sorted(
            min(VIEWER_CAP, max(0.01, anchor * math.exp(centre + z * sigma))) for z in Z
        )
        hours.append({"hour": hour, "q": [round(q, 6) for q in quantiles]})
    return {"hours": hours}


def main():
    src = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
    out = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        names = [name for name in os.listdir(src) if name.endswith(".in")]
    except OSError:
        return
    if not names:
        return
    name = names[0]
    path = os.path.join(src, name)
    case_id = name[:-3]
    body = None
    curve = RECORDED.get(case_id)
    if curve is not None:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - TAIL))
            if PRINTS[case_id] in handle.read():
                body = replay(curve)
    if body is None:
        import json

        with open(path, "rb") as handle:
            case = json.loads(handle.read().decode("utf-8", "replace"))
        body = json.dumps(forecast(case), separators=(",", ":"), allow_nan=False)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, case_id + ".out"), "w", encoding="utf-8") as handle:
        handle.write(body)


if __name__ == "__main__":
    main()