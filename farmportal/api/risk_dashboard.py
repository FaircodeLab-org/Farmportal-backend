# your_app/your_app/api/risk_dashboard.py

from __future__ import annotations
import json
import math
import datetime
from typing import List, Dict, Any

import frappe

# ---- Google Earth Engine setup ----
# Install server deps and ee in your environment, then:
# bench pip install earthengine-api

try:
    import ee
    _EE_READY = False

    def _ee_init_once():
        global _EE_READY
        if _EE_READY:
            return
        # Expect these in site_config.json
        # {
        #   "ee_service_account": "svc@project.iam.gserviceaccount.com",
        #   "ee_private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
        # }
        svc = frappe.conf.get("ee_service_account")
        key = frappe.conf.get("ee_private_key")
        if not svc or not key:
            # We’ll allow non-EE endpoints to continue working
            frappe.logger().warning("Earth Engine credentials missing in site_config.")
            return
        creds = ee.ServiceAccountCredentials(svc, key_data=key)
        ee.Initialize(creds)
        _EE_READY = True
except Exception as _e:
    ee = None
    _EE_READY = False
    frappe.logger().error(f"Failed to import/initialize earthengine-api: {_e}")


# -------------------------------
# Helpers
# -------------------------------

def _safe_now_iso() -> str:
    return datetime.datetime.utcnow().isoformat()

def _parse_polygon_from_geojson(geojson_str: str) -> List[List[float]]:
    """
    Accepts a GeoJSON string of either:
    - Feature with Polygon geometry
    - Polygon geometry
    Returns coordinates in [ [lng, lat], ... ] ring (closed).
    """
    if not geojson_str:
        raise ValueError("Missing GeoJSON.")
    gj = json.loads(geojson_str)

    if gj.get("type") == "Feature":
        geom = gj.get("geometry") or {}
    else:
        geom = gj

    if geom.get("type") != "Polygon":
        raise ValueError("Only Polygon geometries are supported.")

    # Use the exterior ring only
    coords = geom.get("coordinates", [])
    if not coords or not coords[0]:
        raise ValueError("Invalid polygon coordinates.")

    ring = coords[0]
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    return ring

def _grade_deforestation_percent(pct: float) -> str:
    # Adjust thresholds as you like
    if pct >= 5.0:
        return "high"
    return "low"

def _compute_compliance(deforestation_pct: float, docs_complete: bool, geo_complete: bool) -> int:
    """
    Very simple scoring heuristic (0-100). Tune as needed.
    """
    base = 100
    # Penalize deforestation
    base -= min(60, int(deforestation_pct * 8))  # 5% -> -40, 10% -> -60
    if not docs_complete:
        base -= 20
    if not geo_complete:
        base -= 20
    return max(0, min(100, base))

def _risk_level(deforestation_risk: str, compliance: int) -> str:
    if deforestation_risk == "high" or compliance < 40:
        return "high"
    if compliance < 70:
        return "medium"
    return "low"

def _issues_count(deforestation_pct: float, docs_complete: bool, geo_complete: bool) -> int:
    issues = 0
    if deforestation_pct >= 1.0:
        issues += 1
    if not docs_complete:
        issues += 1
    if not geo_complete:
        issues += 1
    return issues


# -------------------------------
# Earth Engine core computation
# -------------------------------

def _ee_tree_loss_stats_from_ring(ring: List[List[float]]) -> Dict[str, Any]:
    _ee_init_once()
    if not _EE_READY or not ee:
        # If EE is unavailable, degrade gracefully
        return {
            "forest_area_ha": 0.0,
            "loss_area_ha": 0.0,
            "deforestation_percent": 0.0,
            "deforestation_tile_url": "",
            "tree_cover_tile_url": ""
        }

    polygon = ee.Geometry.Polygon([ring])

    gfc = ee.Image("UMD/hansen/global_forest_change_2024_v1_12")
    tree_cover_2000 = gfc.select("treecover2000")
    loss_year = gfc.select("lossyear")

    forest_mask = tree_cover_2000.gte(30)
    loss_after_2020 = loss_year.gt(20)

    pixel_area = ee.Image.pixelArea()
    forest_area_img = forest_mask.multiply(pixel_area)
    loss_area_img = loss_after_2020.multiply(forest_mask).multiply(pixel_area)

    forest_area = forest_area_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=polygon,
        scale=30,
        maxPixels=1e9
    ).get('treecover2000')

    loss_area = loss_area_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=polygon,
        scale=30,
        maxPixels=1e9
    ).get('lossyear')

    deforestation_vis = {"min": 1, "max": 1, "palette": ["red"]}
    deforestation_tile_info = loss_after_2020.selfMask().getMapId(deforestation_vis)

    tree_cover_vis = {"min": 30, "max": 100, "palette": ["#d9f0a3", "#31a354"]}
    tree_cover_tile_info = tree_cover_2000.selfMask().getMapId(tree_cover_vis)

    forest_area_ha = ee.Number(forest_area).divide(10000)
    loss_area_ha = ee.Number(loss_area).divide(10000)
    loss_percent = ee.Algorithms.If(
        forest_area_ha.gt(0),
        loss_area_ha.divide(forest_area_ha).multiply(100),
        0
    )

    stats = ee.Dictionary({
        "forest_area_ha": forest_area_ha,
        "loss_area_ha": loss_area_ha,
        "deforestation_percent": loss_percent
    }).getInfo()

    return {
        "forest_area_ha": round(stats["forest_area_ha"], 2),
        "loss_area_ha": round(stats["loss_area_ha"], 2),
        "deforestation_percent": round(stats["deforestation_percent"], 2),
        "deforestation_tile_url": deforestation_tile_info['tile_fetcher'].url_format,
        "tree_cover_tile_url": tree_cover_tile_info['tile_fetcher'].url_format
    }


# -------------------------------
# Public APIs (for frontend)
# -------------------------------

@frappe.whitelist()
def get_tree_loss_tile_url(coordinates_json: str) -> Dict[str, Any]:
    """
    Input: coordinates_json -> '[ [lng,lat], [lng,lat], ... ]'
    Returns: tile URLs + stats
    """
    try:
        ring = json.loads(coordinates_json)
        if not isinstance(ring, list) or not ring:
            raise ValueError("Invalid coordinates payload.")
        if ring[0] != ring[-1]:
            ring.append(ring[0])

        return _ee_tree_loss_stats_from_ring(ring)
    except Exception as e:
        frappe.throw(f"Error generating tile URLs: {str(e)}")


@frappe.whitelist()
def trigger() -> Dict[str, Any]:
    """
    Batch risk analysis for all Suppliers.
    Writes computed fields back onto the Supplier doctype.
    """
    suppliers = frappe.get_all(
        "Supplier",
        fields=["name", "supplier_name", "country", "geojson", "geo_data_complete", "documents_complete"]
    )

    updated = 0
    failed = []

    for sp in suppliers:
        try:
            ring = _parse_polygon_from_geojson(sp.get("geojson")) if sp.get("geojson") else None

            if ring:
                stats = _ee_tree_loss_stats_from_ring(ring)
                defo_pct = float(stats["deforestation_percent"])
                defo_risk = _grade_deforestation_percent(defo_pct)
            else:
                # No geometry => cannot compute deforestation; treat as low by default
                defo_pct = 0.0
                defo_risk = "low"
                stats = {
                    "forest_area_ha": 0.0,
                    "loss_area_ha": 0.0,
                    "deforestation_percent": 0.0,
                    "deforestation_tile_url": "",
                    "tree_cover_tile_url": ""
                }

            compliance = _compute_compliance(
                deforestation_pct=defo_pct,
                docs_complete=bool(sp.get("documents_complete")),
                geo_complete=bool(sp.get("geo_data_complete")),
            )
            risk_level = _risk_level(deforestation_risk=defo_risk, compliance=compliance)
            issues = _issues_count(
                deforestation_pct=defo_pct,
                docs_complete=bool(sp.get("documents_complete")),
                geo_complete=bool(sp.get("geo_data_complete")),
            )

            # Write back to Supplier (create fields in Customize Form if needed)
            doc = frappe.get_doc("Supplier", sp["name"])
            doc.update({
                "last_analysis": _safe_now_iso(),
                "risk_level": risk_level.capitalize(),        # "Low"/"Medium"/"High"
                "compliance_score": compliance,               # 0-100
                "issues_count": issues,
                "deforestation_risk": defo_risk.capitalize()  # "Low"/"High"
            })
            doc.save(ignore_permissions=True)
            updated += 1
        except Exception as e:
            failed.append({"supplier": sp.get("name"), "error": str(e)})
            frappe.logger().error(f"Risk analysis failed for Supplier {sp.get('name')}: {e}")

    frappe.db.commit()
    return {"ok": True, "updated": updated, "failed": failed}


@frappe.whitelist()
def get_suppliers_with_risk() -> Dict[str, Any]:
    """
    Returns suppliers in the exact shape your RiskDashboard.jsx expects.
    """
    rows = frappe.get_all(
        "Supplier",
        fields=[
            "name as _id",
            "supplier_name",
            "country",
            "risk_level",
            "compliance_score",
            "issues_count",
            "deforestation_risk",
            "geo_data_complete",
            "documents_complete",
            "last_analysis"
        ],
        order_by="supplier_name asc"
    )

    suppliers = []
    for r in rows:
        suppliers.append({
            "_id": r["_id"],
            "supplier_name": r.get("supplier_name") or r["_id"],
            "country": r.get("country"),
            "riskLevel": (r.get("risk_level") or "Low").lower(),
            "compliance": int(r.get("compliance_score") or 0),
            "issues": int(r.get("issues_count") or 0),
            "deforestationRisk": (r.get("deforestation_risk") or "Low").lower(),
            "geoDataComplete": bool(r.get("geo_data_complete")),
            "documentsComplete": bool(r.get("documents_complete")),
            "lastAnalysis": r.get("last_analysis")
        })

    # Summary block for your cards
    summary = {
        "totalSuppliers": len(suppliers),
        "highRisk": sum(1 for s in suppliers if s["riskLevel"] == "high"),
        "mediumRisk": sum(1 for s in suppliers if s["riskLevel"] == "medium"),
        "lowRisk": sum(1 for s in suppliers if s["riskLevel"] == "low"),
        "pendingAnalysis": sum(
            1 for s in suppliers
            if (not s["lastAnalysis"]) or _is_older_than_days(s["lastAnalysis"], 7)
        ),
    }

    return {"suppliers": suppliers, "summary": summary}


def _is_older_than_days(iso_dt: str, days: int) -> bool:
    try:
        dt = datetime.datetime.fromisoformat(iso_dt.replace("Z", "+00:00"))
    except Exception:
        return True
    return (datetime.datetime.utcnow() - dt.replace(tzinfo=None)).days > days
