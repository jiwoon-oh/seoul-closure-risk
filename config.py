import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "outputs" / "figures"
for p in (RAW, PROC, FIG):
    p.mkdir(parents=True, exist_ok=True)

# Reproducibility: every random draw (bootstrap, permutation, matching shuffle, models) comes from this one seed.
SEED = 42

# =====================================================================================
# SOURCE NAME TABLES (Korean is allowed ONLY in this block)
# The source files, their columns and their category values are Korean. Everything the
# notebooks see is English: `standardize_source` renames and translates right after loading,
# and anything not listed here raises an error instead of passing through silently.
# BEGIN SOURCE NAMES
# =====================================================================================
ENCODING = "cp949"

# File name patterns look like "서울시 상권분석서비스(점포-상권)_2023년.csv"; spaces and underscores differ
# between files, so names are normalized before comparing.
def _normalize(name: str) -> str:
    # Drop brackets and hyphens too: depending on the download path "(점포-상권)" is sometimes saved as
    # "점포상권". Both sides are normalized the same way. The commercial-area vs district tables
    # stay distinguishable ("점포상권" vs "점포자치구").
    for ch in " _()-":
        name = name.replace(ch, "")
    return name

# Tables are told apart by the table name inside the brackets (never overlaps with the district versions).
TABLE_MARKER = {
    "store":    "(점포-상권)",
    "sales":    "(추정매출-상권)",
    "area":     "(영역-상권)",
    "flow":     "(길단위인구-상권)",
    "facility": "(집객시설-상권)",
    "change":   "(상권변화지표-상권)",   # benchmark only; never used as a feature
}
_YEAR_TOKENS = ["2023년", "2024년", "2025년", "2026년"]

# key -> (table, year token, or None = the latest file without a year token)
FILE_SPEC = {
    "store_2023":  ("store", "2023년"),
    "store_2024":  ("store", "2024년"),
    "store_2025":  ("store", None),
    "sales_2023":  ("sales", "2023년"),
    "sales_2024":  ("sales", "2024년"),
    "sales_2025":  ("sales", "2025년"),
    "sales_late":  ("sales", None),
    "area":        ("area", None),
    "flow":        ("flow", None),
    "facility":    ("facility", None),
    "change":      ("change", None),
}

# Source column -> English name. Only these columns are carried into the project; every other
# source column is dropped at load. Names and codes of commercial areas / administrative dongs are
# deliberately NOT carried (Korean proper names; join `area_code` to the source to get them).
COL_MAP = {
    "기준_년분기_코드": "quarter_code",
    "상권_구분_코드": "area_type_code",
    "상권_구분_코드_명": "area_type_name",
    "상권_코드": "area_code",
    "자치구_코드": "district_code",
    "자치구_코드_명": "district_name",
    "행정동_코드": "admin_dong_code",
    "엑스좌표_값": "x_coord",
    "와이좌표_값": "y_coord",
    "영역_면적": "area_size",
    "서비스_업종_코드": "service_code",
    "서비스_업종_코드_명": "service_name",
    "전체_점포_수": "store_count",
    "일반_점포_수": "nonfranchise_store_count",
    "프랜차이즈_점포_수": "franchise_store_count",
    "점포_수": "legacy_nonfranchise_store_count",
    "유사_업종_점포_수": "legacy_total_store_count",
    "개업_점포_수": "opening_count",
    "폐업_점포_수": "closure_count",
    "집객시설_수": "attracting_facility_count",
    "지하철_역_수": "subway_station_count",
    "당월_매출_금액": "monthly_sales",
    "당월_매출_건수": "monthly_sales_count",
    "총_유동인구_수": "foot_traffic_total",
    "연령대_20_유동인구_수": "foot_traffic_age_20",
    "연령대_30_유동인구_수": "foot_traffic_age_30",
    "연령대_60_이상_유동인구_수": "foot_traffic_age_60_plus",
    "시간대_11_14_유동인구_수": "foot_traffic_time_11_14",
    "시간대_17_21_유동인구_수": "foot_traffic_time_17_21",
    "시간대_21_24_유동인구_수": "foot_traffic_time_21_24",
    "토요일_유동인구_수": "foot_traffic_sat",
    "일요일_유동인구_수": "foot_traffic_sun",
    "상권_변화_지표": "area_change_indicator",
    "운영_영업_개월_평균": "avg_operating_months",
    "서울_운영_영업_개월_평균": "seoul_avg_operating_months",
}
assert len(set(COL_MAP.values())) == len(COL_MAP), "two source columns map to the same English name"

# The ten food categories are chosen by code (the codes stay the same even if Seoul renames a category).
# Source name -> English name; the source name is only used to check that the file still means what we think.
SVC_SOURCE = {
    "CS100001": "한식음식점",
    "CS100002": "중식음식점",
    "CS100003": "일식음식점",
    "CS100004": "양식음식점",
    "CS100005": "제과점",
    "CS100006": "패스트푸드점",
    "CS100007": "치킨전문점",
    "CS100008": "분식전문점",
    "CS100009": "호프-간이주점",
    "CS100010": "커피-음료",
}
SVC_EN = {
    "한식음식점": "Korean restaurants",
    "중식음식점": "Chinese restaurants",
    "일식음식점": "Japanese restaurants",
    "양식음식점": "Western restaurants",
    "제과점": "Bakeries",
    "패스트푸드점": "Fast-food restaurants",
    "치킨전문점": "Fried-chicken shops",
    "분식전문점": "Korean snack-food restaurants",
    "호프-간이주점": "Beer and casual pubs",
    "커피-음료": "Coffee and beverages",
}
AREA_TYPE_EN = {
    "골목상권": "neighborhood commercial area",
    "발달상권": "developed commercial area",
    "전통시장": "traditional market",
    "관광특구": "tourist special zone",
}
DISTRICT_EN = {
    "강남구": "Gangnam-gu", "강동구": "Gangdong-gu", "강북구": "Gangbuk-gu", "강서구": "Gangseo-gu",
    "관악구": "Gwanak-gu", "광진구": "Gwangjin-gu", "구로구": "Guro-gu", "금천구": "Geumcheon-gu",
    "노원구": "Nowon-gu", "도봉구": "Dobong-gu", "동대문구": "Dongdaemun-gu", "동작구": "Dongjak-gu",
    "마포구": "Mapo-gu", "서대문구": "Seodaemun-gu", "서초구": "Seocho-gu", "성동구": "Seongdong-gu",
    "성북구": "Seongbuk-gu", "송파구": "Songpa-gu", "양천구": "Yangcheon-gu", "영등포구": "Yeongdeungpo-gu",
    "용산구": "Yongsan-gu", "은평구": "Eunpyeong-gu", "종로구": "Jongno-gu", "중구": "Jung-gu",
    "중랑구": "Jungnang-gu",
}
# =====================================================================================
# END SOURCE NAMES
# =====================================================================================

# -- Category order (fixed) ---------------------------------------------------------
# groupby / pivot / get_dummies / sort_values follow the order of a Categorical, so every
# category column is converted once at load. The order below is the one the pipeline had when the
# source names were still Korean (sorted by the Korean name), kept so that row order, dummy
# column order and every number stay the same after the rename. It does NOT follow the
# English names' alphabetical order.
SVC_CODES = {c: SVC_EN[k] for c, k in SVC_SOURCE.items()}      # code -> English name, in code order
FOOD = list(SVC_CODES.values())
SVC_ORDER = [SVC_EN[k] for k in sorted(SVC_EN)]
AREA_TYPE_ORDER = [AREA_TYPE_EN[k] for k in sorted(AREA_TYPE_EN)]
DISTRICT_ORDER = [DISTRICT_EN[k] for k in sorted(DISTRICT_EN)]
CATEGORY_ORDER = {
    "service_name": SVC_ORDER,
    "area_type_name": AREA_TYPE_ORDER,
    "area_type": AREA_TYPE_ORDER,
    "district_name": DISTRICT_ORDER,
    "district": DISTRICT_ORDER,
}
_CARRIED = set(COL_MAP.values())


def _find_file(key: str) -> Path:
    table, year = FILE_SPEC[key]
    marker = _normalize(TABLE_MARKER[table])

    candidates = []
    for f in RAW.glob("*.csv"):
        norm = _normalize(f.name)
        if marker not in norm:
            continue
        if year is None:
            # only files with no year token at all (the latest / cumulative file)
            if not any(_normalize(y) in norm for y in _YEAR_TOKENS):
                candidates.append(f)
        else:
            if _normalize(year) in norm:
                candidates.append(f)

    if len(candidates) == 0:
        all_files = "\n".join(f"    - {f.name}" for f in sorted(RAW.glob("*.csv"))) or "    (no files)"
        raise FileNotFoundError(
            f"\n[{key}] no file matches table marker={TABLE_MARKER[table]!r}, year={year!r}.\n"
            f"  Files found in {RAW}:\n{all_files}"
        )
    if len(candidates) > 1:
        names = "\n".join(f"    - {c.name}" for c in candidates)
        raise FileNotFoundError(f"\n[{key}] several candidate files:\n{names}")
    return candidates[0]

class _FilePaths:
    def __getitem__(self, key):
        return _find_file(key).name

    def keys(self):
        return FILE_SPEC.keys()

    def items(self):
        for k in FILE_SPEC:
            try:
                yield k, self[k]
            except FileNotFoundError:
                yield k, None   # files that cannot be found are shown as None


FILES = _FilePaths()


def _translate_values(s, mapping, col):
    """Source category values -> English. A value that is not in the table raises (it never passes through)."""
    unknown = sorted(set(s.dropna().unique()) - set(mapping))
    if unknown:
        raise ValueError(f"{col}: values not in the mapping table: {unknown}")
    return s.map(mapping)


def standardize_source(df):
    """Rename source columns to English, drop columns the project never uses, translate category values
    (strictly) and fix the category order. Called right after reading each source file."""
    import pandas as pd
    df = df.rename(columns=COL_MAP)
    df = df[[c for c in df.columns if c in _CARRIED]].copy()
    if "area_type_name" in df:
        df["area_type_name"] = _translate_values(df["area_type_name"], AREA_TYPE_EN, "area_type_name")
    if "district_name" in df:
        df["district_name"] = _translate_values(df["district_name"], DISTRICT_EN, "district_name")
    if "service_name" in df and "service_code" in df:
        # only the ten food categories are named; the other categories are never used by name
        food = df["service_code"].isin(SVC_SOURCE)
        got = df.loc[food, ["service_code", "service_name"]].drop_duplicates()
        bad = got[got["service_name"] != got["service_code"].map(SVC_SOURCE)]
        if len(bad):
            raise ValueError(f"service_name no longer matches the expected source name for: {bad.values.tolist()}")
        df["service_name"] = df["service_name"].where(food).map(SVC_EN)
    for col, order in CATEGORY_ORDER.items():
        if col in df:
            df[col] = pd.Categorical(df[col], categories=order, ordered=True)
    return df


def dummies(s, prefix, drop_first=False):
    """get_dummies that follows the fixed category order and, like the pre-rename code, only creates
    columns for categories that occur in `s` (a Categorical would otherwise add all-zero columns)."""
    import pandas as pd
    d = pd.get_dummies(s, prefix=prefix)
    d = d.loc[:, d.any()]
    return d.iloc[:, 1:] if drop_first else d


# -- Analysis scope -------------------------------
# 13 quarters are loaded. The label y(t) = [net decline in t+1] needs t+1 to be in this list, so the
# labeled span is 20231-20254 (12 quarters) and 20261 has no label (the forecast target).
QUARTERS = [
    20231, 20232, 20233, 20234,
    20241, 20242, 20243, 20244,
    20251, 20252, 20253, 20254,
    20261
]

# -- Time split -----------------------------------
# A row is (commercial area, service category, feature quarter t) and the label is y(t) = [net decline in t+1].
# The feature quarter and the target quarter are one step apart, so the table below is the single source of truth.
#
#   purpose   feature quarter t   target quarter t+1   label
#   train     20231 ~ 20253       20232 ~ 20254        yes
#   valid     20254               20261                yes
#   score     20261               20262                no
#
# WARNING: putting VALID_Q (20254) in the training set leaks the 20261 outcome.
SCORE_Q = 20261                                    # forecast target (no label)
VALID_Q = 20254                                    # validation (target = SCORE_Q)
TRAIN_QUARTERS = [q for q in QUARTERS if q not in (VALID_Q, SCORE_Q)]
LABELED_QUARTERS = [q for q in QUARTERS if q != SCORE_Q]

# Rolling-origin validation: repeat while moving the end of the training span. Each element is that repetition's validation feature quarter.
ROLLING_VALID = [20243, 20244, 20251, 20252, 20253, 20254]

# -- Store table schema harmonization ----------------------
# The 2023-2024 files and the 2025+ files differ not only in column names: the meaning of the store count differs.
#
#   2023, 2024 :  legacy_total_store_count = legacy_nonfranchise_store_count + franchise_store_count   (match rate 1.000)
#   2025+      :  store_count              = nonfranchise_store_count        + franchise_store_count   (match rate 1.000)
#
# So the old files' `legacy_nonfranchise_store_count` is not the total store count but the
# non-franchise count. The 2025 revision renamed it to `nonfranchise_store_count` and gave the total the name
# `store_count`. The mapping below aligns the old files with the new names.
STORE_RENAME_OLD = {
    "legacy_nonfranchise_store_count": "nonfranchise_store_count",
    "legacy_total_store_count":        "store_count",
}

# Columns kept from the store table
STORE_KEEP = [
    "quarter_code", "area_type_name", "area_code",
    "service_code", "service_name",
    "store_count", "nonfranchise_store_count", "franchise_store_count",
    "opening_count", "closure_count",
]
# Columns kept from the sales table (out of the 55 source columns)
SALES_KEEP = [
    "quarter_code", "area_code", "service_code",
    "monthly_sales", "monthly_sales_count",
]

TARGET_TYPE = "neighborhood commercial area"
TREAT_SVC = "Korean restaurants"
MIN_STORES = 5
COVARIATES = ["log_store_count", "log_foot_traffic", "log_area_size", "log_attracting_facilities"]


# -- Prediction features (shared by STEP 8 and 9) -----------------
# Training (STEP 8) and forecasting (STEP 9) must build the features with the same code.
# Fixing only one side creates train/serve skew, which silently produces wrong predictions.
#
# WARNING: no quarter dummies. The forecast quarter (20261) is not in the training data, so its
# dummy cannot be created, and if it were it would be all zeros and meaningless.

PRED_NUM = [
    "log_store_count", "log_foot_traffic", "log_area_size", "log_attracting_facilities",
    "food_service_share", "franchise_share",
    "opening_rate", "closure_rate", "net_change_rate", "net_decline_now",
    "log_sales_per_store", "sales_missing",
]


def build_features(f):
    """Attach the derived prediction variables to 03_panel.pkl / 03_score.pkl."""
    import numpy as np
    f = f.copy()
    denom = f["store_count"].replace(0, np.nan)
    f["opening_rate"]   = f["opening_count"] / denom
    f["closure_rate"]   = f["closure_count"] / denom
    f["net_change_rate"] = (f["opening_count"] - f["closure_count"]) / denom
    if "net_decline_now" not in f.columns:
        f["net_decline_now"] = ((f["opening_count"] - f["closure_count"]) < 0).astype(int)
    f["log_sales_per_store"] = np.log1p(f["monthly_sales"] / denom)
    f["sales_missing"]      = f["monthly_sales"].isna().astype(float)
    return f


def design_matrix(f, columns=None):
    """Design matrix. With `columns`, reorder to that order and composition (missing dummies become 0)."""
    import pandas as pd
    X = pd.concat([
        f[PRED_NUM],
        dummies(f["service_name"], prefix="svc").astype(float),
        dummies(f["district"], prefix="gu").astype(float),
        dummies(f["area_type"], prefix="tp").astype(float),
    ], axis=1)
    return X if columns is None else X.reindex(columns=columns, fill_value=0.0)


def set_plot_style():
    import matplotlib.pyplot as plt
    plt.rcParams["axes.unicode_minus"] = False   # plain hyphen-minus on axes
    plt.rcParams["figure.dpi"] = 110


# -- Reproducibility tools ----------------------------
# So that ties never depend on row order, ties are broken by the key order below.
TIE_KEYS = ["area_code", "service_code", "quarter_idx"]


def stable_rank(frame, col, keys=None):
    """Rank 1..n by `col`. Ties are broken by the order of `keys` (rank(method="first") follows row order, so it is not used)."""
    import numpy as np
    import pandas as pd
    assert frame.index.is_unique, "the index must be unique"
    ks = [k for k in (TIE_KEYS if keys is None else keys) if k in frame.columns]
    order = frame.sort_values([col] + ks, kind="mergesort").index
    r = pd.Series(np.arange(1, len(frame) + 1, dtype=float), index=order).reindex(frame.index)
    return r.where(frame[col].notna())


def rank_order(score, frame, keys=None):
    """Positions in descending score order. Equal scores are broken by the order of `keys` (the tie order of np.argsort(-score) is unstable)."""
    import numpy as np
    ks = [k for k in (TIE_KEYS if keys is None else keys) if k in frame.columns]
    tmp = frame[ks].reset_index(drop=True).assign(_s=-np.asarray(score, dtype=float))
    return tmp.sort_values(["_s"] + ks, kind="mergesort").index.to_numpy()


def nn_match(df, caliper_mult=0.2, replace=False, seed=SEED, exact="quarter_code"):
    """1:1 nearest-neighbor matching on logit(PS). Returns the (treated index, control index) pairs and the caliper. Shared by STEP 6 and 9."""
    import numpy as np
    import pandas as pd
    cal = caliper_mult * df["logit_ps"].std()
    pairs = []
    keys = [k for k in TIE_KEYS if k in df.columns]
    if exact is None:
        groups = [(None, df)]
    elif isinstance(exact, (list, tuple)):
        groups = df.groupby(list(exact))
    else:
        groups = df.groupby(exact)

    for _, sub in groups:
        if keys:
            sub = sub.sort_values(keys, kind="mergesort")      # fix the input order of the shuffle so it does not depend on row order
        tr = sub[sub["treated"] == 1].sample(frac=1, random_state=seed)
        ct = sub[sub["treated"] == 0]
        if len(ct) == 0:
            continue
        cl, cidx = ct["logit_ps"].to_numpy(), ct.index.to_numpy()
        order = np.argsort(cl, kind="stable"); cl, cidx = cl[order], cidx[order]
        used = np.zeros(len(cl), bool)

        for ti, tv in zip(tr.index, tr["logit_ps"].to_numpy()):
            pos = np.searchsorted(cl, tv)
            l, r, best = pos - 1, pos, -1
            while l >= 0 or r < len(cl):          # expand left and right from the insertion position
                dl = tv - cl[l] if l >= 0      else np.inf
                dr = cl[r] - tv if r < len(cl) else np.inf
                if min(dl, dr) > cal:             # outside the caliper: give up
                    break
                if dl <= dr:
                    if replace or not used[l]: best = l; break
                    l -= 1
                else:
                    if replace or not used[r]: best = r; break
                    r += 1
            if best >= 0:
                if not replace:
                    used[best] = True
                pairs.append((ti, cidx[best]))

    return pd.DataFrame(pairs, columns=["t_idx", "c_idx"]), cal


def tie_random_precision(score, y, ks, rng, reps=200):
    """Top-K precision in descending score order, computed `reps` times with random shuffling only among equal scores. Returns (reps, len(ks)).
    For a score with many ties such as the store count, "who is picked first" is arbitrary, so we look at a distribution instead of one deterministic value."""
    import numpy as np
    score = np.asarray(score, dtype=float)
    y = np.asarray(y, dtype=float)
    ks = np.asarray(ks, dtype=int)
    n = len(score)
    out = np.empty((reps, len(ks)))
    for r in range(reps):
        order = np.lexsort((rng.random(n), -score))      # first key: -score, second key: random (shuffles only within ties)
        cs = np.cumsum(y[order])
        out[r] = cs[ks - 1] / ks
    return out


def tie_report(score, ks, name):
    """Report the tie situation of the score and whether a group of ties is cut at each K boundary."""
    import numpy as np
    import pandas as pd
    score = np.asarray(score, dtype=float)
    vals, cnt = np.unique(score, return_counts=True)
    base = {"score": name, "n_cells": len(score), "n_unique": len(vals),
            "n_tied_cells": int(cnt[cnt > 1].sum()), "max_tie_size": int(cnt.max())}
    desc = np.sort(score)[::-1]
    rows = []
    for K in ks:
        thr = desc[K - 1]
        tie_n = int((score == thr).sum())
        taken = int(K - (score > thr).sum())
        rows.append({**base, "K": K, "n_boundary_tied_cells": tie_n, "n_selected_of_tied": taken,
                     "boundary_cuts_tie": tie_n > taken})
    return pd.DataFrame(rows)
