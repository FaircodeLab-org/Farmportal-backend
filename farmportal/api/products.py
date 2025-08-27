# my_app/my_app/api/products.py
import frappe
from typing import List, Dict

@frappe.whitelist()
def get_products(search: str = None, limit_start: int = 0, limit_page_length: int = 200):
    """
    Returns Items with a 'batches' array for each item.
    Call via: /api/method/my_app.api.products.get_products
    Auth: token or logged-in session.
    """
    # --- Item filters ---
    filters = {"disabled": 0}
    if search:
        # quick search on item_code / item_name
        # Note: for large data, prefer fulltext or client-side filtering.
        filters |= {"item_code": ["like", f"%{search}%"]}

    items: List[Dict] = frappe.get_all(
        "Item",
        fields=["name", "item_code", "item_name", "item_group", "stock_uom"],
        filters=filters,
        start=limit_start,
        page_length=limit_page_length,
        order_by="modified desc",
    )

    # collect item codes to fetch batches in one shot
    item_codes = [i["item_code"] for i in items if i.get("item_code")]
    batches_by_item: Dict[str, List[Dict]] = {}

    if item_codes:
        batch_rows = frappe.get_all(
            "Batch",
            fields=["name", "batch_id", "item", "expiry_date", "manufacturing_date"],
            filters={"item": ["in", item_codes]},
            order_by="creation desc",
            limit_page_length=5000,  # increase if you have many
        )
        for b in batch_rows:
            batches_by_item.setdefault(b["item"], []).append({
                "name": b["name"],
                "batch_id": b.get("batch_id"),
                "expiry_date": b.get("expiry_date"),
                "manufacturing_date": b.get("manufacturing_date"),
            })

    # merge batches into items
    for it in items:
        it["batches"] = batches_by_item.get(it.get("item_code"), [])


    return {
        "message": f"Fetched {len(items)} products from ERPNext",
        "data": items,
        "meta": {
            "limit_start": limit_start,
            "limit_page_length": limit_page_length,
            "next_start": limit_start + len(items) if len(items) == limit_page_length else None,
        },
    }
