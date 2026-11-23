# =============================================================================
# OsdagBridge Report — data extraction layer
# =============================================================================
# Pure functions that pull report-ready values out of the design
# ``input_dict`` / ``output_dict``.  They contain NO LaTeX and NO plotting, so
# that tables (chapters), charts (charts.py) and unit tests share exactly the
# same numbers.
#
#   * Live loads      : selected IRC vehicles + footway load      (Chapter 3)
#   * Utilization     : Demand / Capacity for girders, deck slab,
#                       cross bracing and end diaphragms          (Section 5.5)
#   * Quantities      : steel tonnage, concrete volume, rebar     (Chapter 7)
#
# Rules followed everywhere in this module
#   - values come only from the design results / code-provision functions that
#     OsdagBridge already uses; nothing is invented;
#   - a missing / non-numeric / zero-capacity entry is returned with
#     ``status = "no_data"`` and is never counted as a passing check.
# =============================================================================

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from osdagbridge.core.utils.common import (
    KEY_BL_ECCENTRICITY,
    KEY_BL_IRC_70R_BOGIE,
    KEY_BL_IRC_70R_TRACKED,
    KEY_BL_IRC_70R_WHEELED,
    KEY_BL_IRC_AA_TRACKED,
    KEY_BL_IRC_AA_WHEELED,
    KEY_BL_IRC_CLASS_A,
    KEY_BL_IRC_CLASS_FATIGUE,
    KEY_BL_IRC_CLASS_SV,
    KEY_FOOTPATH,
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_ECCENTRICITY,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_SPAN,
    KEY_TS_FOOTPATH_WIDTH,
    KEY_TS_NO_OF_FOOTPATHS,
    KEY_WC_LD_LANE_TABLE_COUNT,
)

logger = logging.getLogger(__name__)

PASS, FAIL, NO_DATA = "pass", "fail", "no_data"


# =============================================================================
# Generic numeric helpers
# =============================================================================
def to_float(value: Any) -> Optional[float]:
    """Return a finite float or None (never raises)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(str(value).strip()) if isinstance(value, str) else float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def is_truthy(value: Any) -> bool:
    """Interpret GUI checkbox values (bool, 'True', 1, 'yes' …)."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"true", "1", "yes", "y", "checked"}


# =============================================================================
# 1. LIVE LOADS (Chapter 3)
# =============================================================================
@dataclass
class VehicleRow:
    """One selected vehicle class for the Vehicle Live Load table."""
    name: str
    total_load_kN: Optional[float]
    total_load_source: str
    impact_factor: Optional[float]          # 1 + IM
    impact_clause: str
    braking_considered: Optional[bool]      # None = governed by code (no GUI flag)
    custom: bool = False


def _irc6():
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017
    return IRC6_2017


def _sum_point_loads_kN(vehicle: dict) -> Optional[float]:
    """Total of the point (wheel/axle) loads of an IRC6_2017 vehicle, in kN.

    IRC6_2017 expresses these loads in N (``t = 9.81 kN`` in SI base units).
    """
    loads = vehicle.get("wheel_loads")
    if not loads:
        return None
    vals = [to_float(v) for v in loads]
    if any(v is None for v in vals):
        return None
    return sum(vals) / 1000.0


def _class_a_total() -> Optional[float]:
    return _sum_point_loads_kN(_irc6().cl_204_1_ClassA_vehicle())


def _class_70r_wheeled_total() -> Optional[float]:
    return _sum_point_loads_kN(_irc6().cl_204_1_Class70R_vehicle_wheel())


def _class_70r_tracked_total() -> Optional[float]:
    v = _irc6().cl_204_1_Class70R_vehicle_track()
    udl = to_float(v.get("wheel_loads_udl"))          # N/m per track
    xs = v.get("x") or []
    n_tracks = len(v.get("z") or [])
    if udl is None or len(xs) < 2 or not n_tracks:
        return None
    length = to_float(xs[-1]) - to_float(xs[0])
    return udl * length * n_tracks / 1000.0


def _class_sv_total() -> Optional[float]:
    return to_float(_irc6().cl_204_5_1_special_vehicle().get("total_load_kN"))


def _fatigue_total() -> Optional[float]:
    return _sum_point_loads_kN(_irc6().cl_204_6_fatigue_load())


# (GUI selection key, display name, braking key, total-load fn, impact group)
# impact group: "A" → IRC 6 Cl. 208.2, "AA70R" → Cl. 208.3, None → not computed
_IRC_VEHICLES: list[tuple[str, str, str, Optional[Callable[[], Optional[float]]], Optional[str]]] = [
    (KEY_LL_IRC_CLASS_A,       "IRC Class A",             KEY_BL_IRC_CLASS_A,       _class_a_total,           "A"),
    (KEY_LL_IRC_70R_WHEELED,   "IRC Class 70R (Wheeled)", KEY_BL_IRC_70R_WHEELED,   _class_70r_wheeled_total, "AA70R"),
    (KEY_LL_IRC_70R_TRACKED,   "IRC Class 70R (Tracked)", KEY_BL_IRC_70R_TRACKED,   _class_70r_tracked_total, "AA70R"),
    (KEY_LL_IRC_70R_BOGIE,     "IRC Class 70R (Bogie)",   KEY_BL_IRC_70R_BOGIE,     None,                     "AA70R"),
    (KEY_LL_IRC_AA_WHEELED,    "IRC Class AA (Wheeled)",  KEY_BL_IRC_AA_WHEELED,    None,                     "AA70R"),
    (KEY_LL_IRC_AA_TRACKED,    "IRC Class AA (Tracked)",  KEY_BL_IRC_AA_TRACKED,    None,                     "AA70R"),
    (KEY_LL_IRC_CLASS_SV,      "IRC Class SV",            KEY_BL_IRC_CLASS_SV,      _class_sv_total,          None),
    (KEY_LL_IRC_CLASS_FATIGUE, "IRC Fatigue Vehicle",     KEY_BL_IRC_CLASS_FATIGUE, _fatigue_total,           None),
]


def _impact_factor(group: Optional[str], span_m: Optional[float]) -> tuple[Optional[float], str]:
    """(1 + IM, clause) exactly as the original Chapter 3 computed it."""
    if group is None or span_m is None:
        return None, "---"
    try:
        if group == "A":
            return 1.0 + _irc6().cl_208_2_impact_factor(span_m), "IRC 6 Cl. 208.2"
        return 1.0 + _irc6().cl_208_3_impact_factor(span_m), "IRC 6 Cl. 208.3"
    except Exception:
        return None, "---"


def selected_vehicles(input_dict: dict) -> list[VehicleRow]:
    """Vehicles ticked in *Additional Inputs → Loading → Live Load*, in GUI order.

    Only vehicles whose checkbox value is truthy are returned; an empty list
    means no vehicle is selected.
    """
    span_m = to_float(input_dict.get(KEY_SPAN))
    rows: list[VehicleRow] = []
    for sel_key, name, bl_key, total_fn, group in _IRC_VEHICLES:
        if not is_truthy(input_dict.get(sel_key)):
            continue
        total = None
        source = "not defined in the OsdagBridge IRC 6 vehicle library"
        if total_fn is not None:
            try:
                total = total_fn()
                source = "IRC 6 Cl. 204"
            except Exception:
                total = None
        imf, clause = _impact_factor(group, span_m)
        braking = is_truthy(input_dict[bl_key]) if bl_key in input_dict else None
        rows.append(VehicleRow(name, total, source, imf, clause, braking))

    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if isinstance(custom, list):
        for c in custom:
            if isinstance(c, dict) and c.get("name"):
                total = None
                for k in ("total_load_kN", "total_load", "gross_weight_kN"):
                    total = to_float(c.get(k))
                    if total is not None:
                        break
                rows.append(VehicleRow(str(c["name"]), total,
                                       "user-defined" if total is not None else "not provided",
                                       None, "---", None, custom=True))
            elif isinstance(c, str) and c.strip():
                rows.append(VehicleRow(c.strip(), None, "not provided", None, "---", None, custom=True))
    return rows


@dataclass
class BrakingInfo:
    lanes: Optional[int]
    force_kN: Optional[float]
    force_t: Optional[float]
    eccentricity_m: Optional[float]
    lanes_source: str = ""
    # Plain-language reason shown in the report when force_kN is None.  Python
    # exception details never go here; they are written to the log instead.
    unavailable_reason: str = ""


def design_lanes(input_dict: dict) -> tuple[Optional[int], str]:
    """(number of design lanes, source) -- (None, "") when it cannot be determined.

    The lane-table count when the user filled it in; otherwise derived from the
    carriageway width with ``IRC6_2017.table_6`` -- the same rule the grillage
    analyser uses to place the vehicles (single carriageway only).
    """
    from osdagbridge.core.utils.common import KEY_CARRIAGEWAY_WIDTH, KEY_INCLUDE_MEDIAN

    raw_lanes = input_dict.get(KEY_WC_LD_LANE_TABLE_COUNT)
    if raw_lanes not in (None, ""):
        try:
            return int(float(raw_lanes)), "lane table"
        except (TypeError, ValueError):
            pass
    if not is_truthy(input_dict.get(KEY_INCLUDE_MEDIAN)):  # "Yes" -> split carriageway
        cw = to_float(input_dict.get(KEY_CARRIAGEWAY_WIDTH))
        if cw:
            try:
                return int(_irc6().table_6(cw)), "IRC 6 Table 6 (carriageway width)"
            except Exception:
                logger.warning("IRC6_2017.table_6(%s) failed", cw, exc_info=True)
    return None, ""


def braking_info(input_dict: dict) -> BrakingInfo:
    """Braking force (IRC 6 Cl. 211.2, unchanged calculation) and eccentricity.

    ``IRC6_2017.cl_211_2_braking_force`` currently raises ``UnboundLocalError``
    for 1 or 2 lanes (its ``braking_force_2`` term is only assigned for lanes
    > 2).  The engineering function is deliberately not patched here: treating
    the missing term as 0 would drop the Cl. 211.2 "10 % of the succeeding
    trains" contribution and could understate the force.  The value is
    reported as not available and the exception is logged.
    """
    reason = ""
    force_t = None
    lanes, lanes_source = design_lanes(input_dict)
    if lanes is None:
        reason = "the number of design lanes is not available"
    else:
        try:
            force_t = to_float(_irc6().cl_211_2_braking_force(lanes))
            if force_t is None:
                reason = "the braking-force calculation returned no numeric value"
        except Exception:
            force_t = None
            reason = (f"the design pipeline's IRC 6 Cl. 211.2 braking-force function returns "
                      f"no value for {lanes} design lane{'' if lanes == 1 else 's'} "
                      f"(known upstream defect D-18)")
            logger.warning("Braking force not available: IRC6_2017.cl_211_2_braking_force"
                           "(%s) failed", lanes, exc_info=True)
    force_kN = force_t * 9.81 if force_t is not None else None
    ecc = to_float(input_dict.get(KEY_LL_ECCENTRICITY))
    if ecc is None:
        ecc = to_float(input_dict.get(KEY_BL_ECCENTRICITY))
    return BrakingInfo(lanes, force_kN, force_t, ecc, lanes_source, reason)


# Centrifugal force (IRC 6 Cl. 212) acts only on bridges situated on a
# horizontal curve.  OsdagBridge has no plan-curvature input and builds its
# grillage straight in plan (analyser: og.create_grillage(long_dim, width, skew,
# ...) without a curve), so every bridge it designs is straight and the force
# is not applicable.  Should a plan-curvature input ever appear, the value is
# NOT computed by the pipeline and is then reported as not available.
CENTRIFUGAL_NOT_APPLICABLE = ("Not applicable (straight bridge) - IRC 6 Cl. 212 applies to "
                              "bridges on a horizontal curve; this bridge is straight in plan "
                              "(no horizontal-curve input)")
CENTRIFUGAL_NOT_COMPUTED = "Not available - not computed by the design pipeline"
_PLAN_CURVE_KEY_HINTS = ("radius_of_curvature", "horizontal_curve", "plan_radius",
                         "curved_alignment", "horizontal_radius", "alignment_radius")


def centrifugal_text(input_dict: dict) -> str:
    """Text for the centrifugal-force row of Table 3.3 (never a computed value)."""
    for key, val in (input_dict or {}).items():
        if any(h in str(key).lower() for h in _PLAN_CURVE_KEY_HINTS):
            num = to_float(val)
            if (num is not None and num != 0) or (num is None and is_truthy(val)):
                return CENTRIFUGAL_NOT_COMPUTED       # curved: genuinely missing
    return CENTRIFUGAL_NOT_APPLICABLE


@dataclass
class FootwayInfo:
    provision: str                      # "None", "Single Side", "Both Sides"
    applicable: bool
    n_footpaths: Optional[int]
    width_m: Optional[float]
    pressure_mode: str
    pressure_kN_m2: Optional[float]
    pressure_source: str


def footway_info(input_dict: dict) -> FootwayInfo:
    """Footway (footpath) live-load parameters from the Loading tab."""
    provision = str(input_dict.get(KEY_FOOTPATH, "None") or "None").strip()
    applicable = provision.lower() not in ("none", "")
    n_fp = to_float(input_dict.get(KEY_TS_NO_OF_FOOTPATHS))
    width = to_float(input_dict.get(KEY_TS_FOOTPATH_WIDTH))
    mode = str(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "") or "").strip()
    pressure, source = None, "---"
    if mode.lower() in ("as per irc 6", "as per irc6", "automatic"):
        try:
            pressure = to_float(_irc6().cl_206_1_footway_load())
            source = "IRC 6 Cl. 206.1"
        except Exception:
            pressure = None
    else:
        pressure = to_float(input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE))
        if pressure is not None:
            source = "user-defined"
    return FootwayInfo(provision, applicable,
                       int(n_fp) if n_fp is not None else None,
                       width, mode or "---", pressure, source)


# =============================================================================
# 2. UTILIZATION RATIOS (Section 5.5)
# =============================================================================
@dataclass
class URItem:
    """One Demand / Capacity check of one structural element."""
    label: str                       # short text used on the chart x-axis
    member: str                      # e.g. "G2", "G1-G2 diagonal"
    check: str                       # e.g. "ULS Flexure", "Compression"
    demand: Optional[float]
    capacity: Optional[float]
    ur: Optional[float]
    status: str                      # PASS / FAIL / NO_DATA
    demand_unit: str = ""
    capacity_unit: str = ""
    governing: str = ""              # governing load case / combination
    source: str = ""                 # where the UR came from
    reason: str = ""                 # why status is NO_DATA
    section: str = ""                # member section designation (bracing members)


UR_LIMIT = 1.0
_UR_TOL = 1e-9


def compute_ur(demand: Any, capacity: Any, reported: Any = None) -> tuple[Optional[float], str, str]:
    """Return ``(ur, status, reason)`` for one check.

    * ``reported`` — a utilization ratio already computed by the design
      module (DCR / Osdag efficiency).  It is authoritative when it is a valid
      non-negative number.
    * otherwise UR = |Demand| / Capacity.
    * missing / non-numeric values or a zero / negative capacity give
      ``status = NO_DATA`` — such a check is never reported as passing.
    """
    r = to_float(reported)
    if r is not None and r >= 0:
        ur, source_reason = r, ""
    else:
        d, c = to_float(demand), to_float(capacity)
        if d is None and c is None:
            return None, NO_DATA, "demand and capacity not available"
        if d is None:
            return None, NO_DATA, "demand not available"
        if c is None:
            return None, NO_DATA, "capacity not available"
        if c <= 0:
            return None, NO_DATA, "capacity is zero or negative"
        ur, source_reason = abs(d) / c, ""
    status = FAIL if ur > UR_LIMIT + _UR_TOL else PASS
    return ur, status, source_reason


def _ur_item(label, member, check, demand, capacity, reported=None, **kw) -> URItem:
    ur, status, reason = compute_ur(demand, capacity, reported)
    return URItem(label=label, member=member, check=check,
                  demand=to_float(demand), capacity=to_float(capacity),
                  ur=ur, status=status, reason=reason, **kw)


# ---- 2a. Steel plate girders --------------------------------------------------
def girder_check_items(output_dict: dict) -> list[URItem]:
    """Every (girder, check) result of the girder design module.

    Source: ``output_dict["design_results"]["per_girder"][G]["checks"]`` (the
    envelope DCR results, also used by Table 5.22).  The module's own
    ``status`` field is respected: a check it marks ``FAIL`` is reported as
    failing even if its DCR were <= 1.0 (the stricter reading wins).
    """
    per_girder = ((output_dict or {}).get("design_results") or {}).get("per_girder") or {}
    items: list[URItem] = []
    for g, gd in per_girder.items():
        if str(g).startswith("EB") or not isinstance(gd, dict):
            continue
        for chk in gd.get("checks") or []:
            name = str(chk.get("name") or f"Check {chk.get('check_id')}")
            item = _ur_item(f"{name} ({g})", str(g), name,
                            chk.get("demand"), chk.get("capacity"), chk.get("dcr"),
                            demand_unit=str(chk.get("demand_unit") or ""),
                            capacity_unit=str(chk.get("capacity_unit") or ""),
                            source="design_results.per_girder (DCR)")
            if item.status == PASS and "FAIL" in str(chk.get("status", "")).upper():
                item.status = FAIL
            items.append(item)
    return items


def per_girder_governing(output_dict: dict) -> dict[str, URItem]:
    """Governing (highest-UR) check of each girder, keyed by girder label."""
    out: dict[str, URItem] = {}
    for it in girder_check_items(output_dict):
        cur = out.get(it.member)
        if cur is None or cur.ur is None or (it.ur is not None and it.ur > cur.ur):
            out[it.member] = it
    return out


def girder_ur_items(output_dict: dict) -> list[URItem]:
    """Governing girder for every girder design check (one item per check name)."""
    best: dict[str, URItem] = {}
    order: list[str] = []
    for item in girder_check_items(output_dict):
        name = item.check
        if name not in best:
            order.append(name)
            best[name] = item
            continue
        cur = best[name]
        # keep the governing (highest valid UR) girder; valid beats no-data;
        # a failing check is never replaced by a passing one
        if (cur.ur is None or (item.ur is not None and item.ur > cur.ur)
                or (item.status == FAIL and cur.status != FAIL)):
            best[name] = item
    return [best[n] for n in order]


# ---- 2b. Concrete deck slab ----------------------------------------------------
def deck_ur_items(output_dict: dict) -> list[URItem]:
    """Deck slab checks from ``output_dict["deck_report_values"]``.

    The deck designer stores Demand and Capacity (no ratio), so
    UR = Demand / Capacity — the same pairs as Table 5.22.
    """
    from osdagbridge.core.utils.common import (
        KEY_DD_HAS_OVERHANG, KEY_DD_M_ULS_HOG, KEY_DD_M_ULS_OH, KEY_DD_M_ULS_SAG,
        KEY_DD_MU_BOT, KEY_DD_MU_OH, KEY_DD_MU_TOP, KEY_DD_PUNCH_VED,
        KEY_DD_SHEAR_VED, KEY_DD_SHEAR_VRDC, KEY_DD_VRD_C_MPA, KEY_DD_WK_BOT,
        KEY_DD_WK_LIMIT, KEY_DD_WK_OH, KEY_DD_WK_TOP,
    )
    dr = (output_dict or {}).get("deck_report_values") or {}
    if not dr:
        return []
    items = [
        _ur_item("Flexure - sagging", "Deck slab", "Flexure (sagging)",
                 dr.get(KEY_DD_M_ULS_SAG), dr.get(KEY_DD_MU_BOT),
                 demand_unit="kNm/m", capacity_unit="kNm/m", source="deck_report_values"),
        _ur_item("Flexure - hogging", "Deck slab", "Flexure (hogging)",
                 dr.get(KEY_DD_M_ULS_HOG), dr.get(KEY_DD_MU_TOP),
                 demand_unit="kNm/m", capacity_unit="kNm/m", source="deck_report_values"),
    ]
    if is_truthy(dr.get(KEY_DD_HAS_OVERHANG)):
        items.append(_ur_item("Cantilever overhang", "Deck slab", "Overhang flexure",
                              dr.get(KEY_DD_M_ULS_OH), dr.get(KEY_DD_MU_OH),
                              demand_unit="kNm/m", capacity_unit="kNm/m",
                              source="deck_report_values"))
    items += [
        _ur_item("Punching shear", "Deck slab", "Punching shear",
                 dr.get(KEY_DD_PUNCH_VED), dr.get(KEY_DD_VRD_C_MPA),
                 demand_unit="MPa", capacity_unit="MPa", source="deck_report_values"),
        _ur_item("One-way shear", "Deck slab", "One-way shear",
                 dr.get(KEY_DD_SHEAR_VED), dr.get(KEY_DD_SHEAR_VRDC),
                 demand_unit="kN/m", capacity_unit="kN/m", source="deck_report_values"),
    ]
    wks = [to_float(dr.get(k)) for k in (KEY_DD_WK_BOT, KEY_DD_WK_TOP, KEY_DD_WK_OH)]
    wks = [w for w in wks if w is not None]
    items.append(_ur_item("Crack width", "Deck slab", "Crack width",
                          max(wks) if wks else None, dr.get(KEY_DD_WK_LIMIT),
                          demand_unit="mm", capacity_unit="mm", source="deck_report_values"))
    return items


# ---- 2c / 2d. Cross bracing and end diaphragms ---------------------------------
def _bracing_ur_items(design_results: dict, forces: dict, element: str) -> list[URItem]:
    """Members designed with the Osdag tension/compression modules.

    ``design_results[pair][member][force_type]`` is the Osdag result; its
    efficiency (UR) and capacity are authoritative.  Demand = governing member
    force from ``forces["pairs"][pair]``.
    """
    from osdagbridge.core.bridge_types.plate_girder.results_data import _extract_osdag_summary

    items: list[URItem] = []
    pairs_forces = (forces or {}).get("pairs") or {}
    for pair in sorted((design_results or {}).keys()):
        members = design_results.get(pair)
        if not isinstance(members, dict):
            continue
        for member in ("diagonal", "chord"):
            by_force = members.get(member)
            if not isinstance(by_force, dict):
                continue
            for force_type in ("compression", "tension"):
                if force_type not in by_force:
                    continue
                summary = _extract_osdag_summary(by_force.get(force_type) or {})
                pf = pairs_forces.get(pair) or {}
                prefix = "diag" if member == "diagonal" else "chord"
                demand = pf.get(f"{prefix}_{force_type}_kN")
                tag = "C" if force_type == "compression" else "T"
                items.append(_ur_item(
                    f"{pair} {member} ({tag})", f"{pair} {member}", force_type.capitalize(),
                    demand, summary.get("capacity_kN"), summary.get("efficiency"),
                    demand_unit="kN", capacity_unit="kN",
                    governing=str(pf.get(f"{prefix}_{force_type}_gov_lc") or ""),
                    source=f"{element} Osdag member design",
                    section=str(summary.get("section") or "")))
    return items


_ED_PFX = "member_properties.end_diaphragm_details."


def end_diaphragm_members(input_dict: dict) -> list[dict]:
    """End-diaphragm members as defined in the input (Additional Inputs).

    One dict per ``<pair>.<member>`` (e.g. ``G1G2.E1M1``) with its type,
    section designations and the section properties stored with the input
    (area in cm², radii of gyration in cm, as in the section database).
    """
    inp = input_dict or {}
    members: dict[tuple, dict] = {}
    for k in inp:
        if not str(k).startswith(_ED_PFX + "type."):
            continue
        rest = str(k)[len(_ED_PFX + "type."):]            # "G1G2.E1M1"
        if "." not in rest:
            continue
        pair, member = rest.split(".", 1)
        sfx = f".{pair}.{member}"

        def g(name):
            v = inp.get(_ED_PFX + name + sfx)
            return v if v not in (None, "") else None

        members[(pair, member)] = {
            "pair": pair, "member": member,
            "type": g("type"), "bracing_type": g("bracing_type"),
            "bracing_section": g("bracing_section_designation"),
            "top_chord_section": g("top_chord_section_designation"),
            "bottom_chord_section": g("bottom_chord_section_designation"),
            "beam_section": g("is_section"),
            "area_cm2": to_float(g("section_properties.area")),
            "r_y_cm": to_float(g("section_properties.radius_gyration_y")),
            "r_z_cm": to_float(g("section_properties.radius_gyration_z")),
        }
    return [members[k] for k in sorted(members)]


def cross_bracing_ur_items(output_dict: dict) -> list[URItem]:
    od = output_dict or {}
    return _bracing_ur_items(od.get("crossbracing_design_results") or {},
                             od.get("crossbracing_forces_dict") or {}, "cross bracing")


def end_diaphragm_ur_items(output_dict: dict) -> list[URItem]:
    od = output_dict or {}
    return _bracing_ur_items(od.get("end_diaphragm_design_results") or {},
                             od.get("end_diaphragm_forces_dict") or {}, "end diaphragm")


def end_diaphragm_type(input_dict: dict) -> str:
    from osdagbridge.core.utils.common import KEY_MP_ED_TYPE
    for k, v in (input_dict or {}).items():
        if str(k).startswith(KEY_MP_ED_TYPE + ".") and v:
            return str(v)
    return ""


def end_diaphragm_no_data_reason(input_dict: dict, output_dict: dict) -> str:
    """Plain-language explanation used when no end-diaphragm URs exist."""
    ed_type = end_diaphragm_type(input_dict)
    if ed_type and "brac" not in ed_type.lower():
        return (f"End diaphragm type is '{ed_type}': OsdagBridge does not yet perform a "
                "Demand/Capacity design check for rolled / welded beam end diaphragms.")
    forces = ((output_dict or {}).get("end_diaphragm_forces_dict") or {}).get("pairs") or {}
    has_force = any(v is not None for pf in forces.values() if isinstance(pf, dict)
                    for k, v in pf.items() if k.endswith("_kN"))
    if not has_force:
        return ("The analysis returned no end-diaphragm member forces, so no end-diaphragm "
                "Demand/Capacity checks were performed.")
    return "No end-diaphragm design results are available."


@dataclass
class UtilizationSummary:
    girders: list[URItem] = field(default_factory=list)
    deck: list[URItem] = field(default_factory=list)
    cross_bracing: list[URItem] = field(default_factory=list)
    end_diaphragms: list[URItem] = field(default_factory=list)
    end_diaphragm_reason: str = ""

    def categories(self) -> list[tuple[str, str, list[URItem]]]:
        """(key, title, items) for the four required structural elements."""
        return [
            ("girders", "Steel Plate Girders", self.girders),
            ("deck", "Concrete Deck Slab", self.deck),
            ("cross_bracing", "Cross Bracing", self.cross_bracing),
            ("end_diaphragms", "End Diaphragms", self.end_diaphragms),
        ]


def collect_utilization(input_dict: dict, output_dict: dict) -> UtilizationSummary:
    """All UR data needed for Section 5.5 (tables + charts)."""
    s = UtilizationSummary(
        girders=girder_ur_items(output_dict),
        deck=deck_ur_items(output_dict),
        cross_bracing=cross_bracing_ur_items(output_dict),
        end_diaphragms=end_diaphragm_ur_items(output_dict),
    )
    if not s.end_diaphragms:
        s.end_diaphragm_reason = end_diaphragm_no_data_reason(input_dict, output_dict)
    return s


def governing(items: list[URItem], check: Optional[str] = None) -> Optional[URItem]:
    """Highest-UR item (optionally only for one check name)."""
    pool = [i for i in items if i.ur is not None and (check is None or i.check == check)]
    return max(pool, key=lambda i: i.ur) if pool else None


# =============================================================================
# 3. MATERIAL QUANTITIES (Chapter 7)
# =============================================================================
@dataclass
class QuantityGroup:
    title: str
    unit: str
    axis_label: str
    labels: list[str]
    values: list[Optional[float]]
    notes: list[str] = field(default_factory=list)


def end_diaphragm_tonnage_note(boq_note) -> str:
    """One-line note under Figure 7.1 when end-diaphragm tonnage is missing.

    Stated, never estimated: no member length is guessed for the frames.
    """
    note = str(boq_note or "")
    if "cross-bracing" in note.lower():
        why = "the member lengths of the cross-bracing end-diaphragm frames are not in the design output"
    elif note:
        why = note.rstrip(".").replace("No end", "no end")
    else:
        why = "the BOQ module did not compute it"
    return f"End-diaphragm tonnage not available (N.A. in Table 7.1): {why}."


def material_quantity_groups(quantities: dict) -> list[QuantityGroup]:
    """Chart data for Chapter 7, taken from the BOQ module's numeric output.

    ``quantities`` is the dict returned by
    ``boq_generator.calculate_material_quantities`` (the same data printed in
    Table 7.1).  Values that the BOQ module could not compute stay None.
    """
    num = (quantities or {}).get("boq_numeric") or {}

    def g(key):
        return to_float(num.get(key))

    bracing_parts = [g("bracing_top_wt_total_t"), g("bracing_bot_wt_total_t"), g("bracing_diag_wt_total_t")]
    bracing = sum(bracing_parts) if all(v is not None for v in bracing_parts) else None

    steel = QuantityGroup(
        title="Structural Steel Tonnage",
        unit="MT", axis_label="Steel weight (MT)",
        labels=["Steel plate girders", "Cross bracing", "End diaphragms"],
        values=[g("steel_girders_wt_total_t"), bracing, g("end_diaphragm_wt_total_t")],
    )
    if steel.values[2] is None:
        steel.notes.append(end_diaphragm_tonnage_note(num.get("end_diaphragm_note")))
    concrete = QuantityGroup(
        title="Concrete Volume",
        unit="m³", axis_label="Concrete volume (m³)",
        labels=["Deck slab", "Crash barriers"],
        values=[g("concrete_deck_vol_total_m3"), g("crash_barrier_vol_total_m3")],
    )
    rebar = QuantityGroup(
        title="Reinforcement Steel",
        unit="MT", axis_label="Reinforcement weight (MT)",
        labels=["Deck slab"],
        values=[g("rebar_deck_wt_total_t")],
    )
    if rebar.values[0] is not None and num.get("rebar_basis"):
        rebar.notes.append(str(num["rebar_basis"]))
    return [steel, concrete, rebar]


# =============================================================================
# 4. UNITS (report-side conversion of stored values)
# =============================================================================
_LENGTH_TO_MM = {"m": 1000.0, "mm": 1.0}


def girder_dimension_source_unit(output_dict: Optional[dict]) -> str:
    """Unit in which the girder ``section_input`` dimensions are stored.

    The GUI stores the girder depth / flange / web dimensions in **mm**.  At the
    start of ``PlateGirderBridge.design()`` the method
    ``_convert_girder_dims_mm_to_m`` converts them, in ``input_dict`` itself, to
    SI **metres** (the analyser and designer work in metres).  The report is
    always built from a copy of ``input_dict`` taken *after* the design run,
    which is recognisable by the presence of ``design_results`` in
    ``output_dict``.  Without design results the GUI values (mm) are reported.
    """
    return "m" if (output_dict or {}).get("design_results") else "mm"


def length_in_mm(value: Any, source_unit: str) -> Optional[float]:
    """Convert a stored length to millimetres (None when not numeric).

    ``source_unit`` must be stated explicitly ("m" or "mm"); a value that is
    already in mm is returned unchanged, so a value is never converted twice.
    """
    if source_unit not in _LENGTH_TO_MM:
        raise ValueError(f"unsupported length unit {source_unit!r}")
    f = to_float(value)
    if f is None:
        return None
    return round(f * _LENGTH_TO_MM[source_unit], 6)    # strip float noise (0.022*1000)


def format_mm(value_mm: Optional[float]) -> str:
    """'1670', '22', '21.1' (no unit); '---' when unavailable."""
    if value_mm is None:
        return "---"
    text = f"{value_mm:.3f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


# =============================================================================
# 5. DESIGN STATUS (Executive Summary, Key Design Outcomes)
# =============================================================================
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NOT_AVAILABLE = "NOT AVAILABLE"
STATUS_INCOMPLETE = "INCOMPLETE"          # no failure, but some checks have no data
STATUS_NOT_VERIFIED = "NOT FULLY VERIFIED"  # overall: no failure, not everything checked


@dataclass
class ComponentStatus:
    key: str
    title: str
    status: str
    governing: Optional[URItem]            # highest valid UR (None if no valid data)
    n_checks: int
    n_valid: int
    failing: list[URItem] = field(default_factory=list)
    reason: str = ""                       # why data is missing (if known)


def component_status(key: str, title: str, items: list[URItem], reason: str = "") -> ComponentStatus:
    """Status of one structural component from its individual checks.

    * FAIL           any check with valid data fails (UR > 1.0 or module FAIL);
    * PASS           every check has valid data and passes (UR <= 1.0);
    * INCOMPLETE     no failure, but at least one check has no valid data;
    * NOT AVAILABLE  no check with valid data at all.
    A pass is never inferred from the absence of failures alone.
    """
    valid = [i for i in items if i.ur is not None and i.status in (PASS, FAIL)]
    failing = [i for i in valid if i.status == FAIL]
    if not valid:
        status = STATUS_NOT_AVAILABLE
    elif failing:
        status = STATUS_FAIL
    elif len(valid) < len(items):
        status = STATUS_INCOMPLETE
    else:
        status = STATUS_PASS
    gov = max(valid, key=lambda i: i.ur) if valid else None
    return ComponentStatus(key, title, status, gov, len(items), len(valid), failing, reason)


def design_status(summary: "UtilizationSummary") -> tuple[list[ComponentStatus], str]:
    """Per-component statuses and the overall bridge status.

    Overall: FAIL if any component fails; PASS only if every component passes;
    otherwise NOT FULLY VERIFIED (missing data is never treated as a pass).
    """
    comps = [component_status(k, t, items,
                              summary.end_diaphragm_reason if k == "end_diaphragms" else "")
             for k, t, items in summary.categories()]
    statuses = {c.status for c in comps}
    if STATUS_FAIL in statuses:
        overall = STATUS_FAIL
    elif statuses == {STATUS_PASS}:
        overall = STATUS_PASS
    else:
        overall = STATUS_NOT_VERIFIED
    return comps, overall


# =============================================================================
# 6. DATA-CONSISTENCY NOTES (upstream issues disclosed in the report)
# =============================================================================
def consistency_notes(input_dict: dict, output_dict: dict) -> dict[str, str]:
    """Plain-language notes about inconsistencies found in the design data.

    The report does not alter the analysis or design output; where that output
    is internally inconsistent the reader is told so.  Keys:
    ``girder_count``, ``cb_spacing``, ``section_properties``.
    """
    from osdagbridge.core.utils.common import (
        KEY_MP_CB_SPACING, KEY_MP_GIRDER_SECTIONAL_AREA, KEY_TS_NO_OF_GIRDERS,
    )
    inp, od = input_dict or {}, output_dict or {}
    dr = od.get("design_results") or {}
    notes: dict[str, str] = {}

    n_in = to_float(inp.get(KEY_TS_NO_OF_GIRDERS))
    names = [g for g in (dr.get("per_girder") or {}) if not str(g).startswith("EB")]
    if n_in is not None and names and len(names) != int(n_in):
        notes["girder_count"] = (
            f"The girder design results contain {len(names)} longitudinal members "
            f"({names[0]}-{names[-1]}) although the bridge has {int(n_in)} girders. The grillage "
            "model adds a longitudinal line at each deck edge, and the design module designs and "
            "labels these edge lines as girders as well. Results are reported with the labels "
            "used by the design module, so these labels do not necessarily denote the girders "
            "numbered in Chapter 2. This is an issue of the analysis/design module (not changed "
            "by the report) and requires engineering verification.")

    used = to_float(dr.get("cross_bracing_spacing_m"))
    if used is None:
        used = to_float(((od.get("crossbracing_forces_dict") or {}).get("geometry") or {}).get("cb_spacing_m"))
    entered = sorted({v for k, v in ((k, to_float(v)) for k, v in inp.items()
                                     if str(k).startswith(KEY_MP_CB_SPACING + "."))
                      if v is not None})
    if used is not None and entered and any(abs(e - used) > 1e-6 for e in entered):
        shown = ", ".join(f"{e:g}" for e in entered)
        notes["cb_spacing"] = (
            f"Cross-bracing spacing: the input lists {shown} m (Table 2.9), but the girder "
            f"design checks and the cross-bracing force calculation used {used:g} m. The design "
            "modules read a spacing value that is not set by the input, so their default was "
            "applied. Requires engineering verification.")

    a_design = to_float(dr.get("A_steel_mm2"))
    a_model = None
    for k, v in inp.items():
        if str(k).startswith(KEY_MP_GIRDER_SECTIONAL_AREA):
            a_model = to_float(v)
            break
    if a_design and a_model and abs(a_model * 1e6 - a_design) / a_design > 0.01:
        notes["section_properties"] = (
            f"Girder section properties: the grillage analysis model uses the stored section "
            f"area {a_model * 1e4:.1f} cm2, whereas the final designed section "
            f"({dr.get('section_designation', 'see Table 5.1')}) has {a_design / 100:.1f} cm2. "
            "Member forces were therefore computed with properties that differ from the checked "
            "section. Requires engineering verification.")

    # Deflection: per-girder load-effect values (Table 4.3) vs the IRC 22 check.
    from osdagbridge.core.utils.common import KEY_SD_DEFL_LIVE, KEY_SD_DEFL_TOTAL

    def _max_suffixed(base):
        vals = [to_float(v) for k, v in od.items() if str(k).startswith(base + ".G")]
        vals = [v for v in vals if v is not None]
        return max(vals) if vals else None

    pg_live, pg_total = _max_suffixed(KEY_SD_DEFL_LIVE), _max_suffixed(KEY_SD_DEFL_TOTAL)
    ck_live, ck_total = to_float(dr.get("delta_live_mm")), to_float(dr.get("delta_total_mm"))

    def _differs(a, b):
        return a is not None and b is not None and b > 0 and abs(a - b) / b > 0.05

    if _differs(pg_live, ck_live) or _differs(pg_total, ck_total):
        notes["deflection"] = (
            f"Deflection: the per-girder load-effect results used in Table 4.3 give "
            f"{pg_live:g} mm (live) and {pg_total:g} mm (total), whereas the IRC 22 deflection "
            f"checks of the girder design module (Section 5.1) use {ck_live:g} mm and "
            f"{ck_total:g} mm. The two calculations of the application disagree, so the "
            "deflection status differs between Table 4.3 and Section 5. Requires engineering "
            "verification.")
    return notes
