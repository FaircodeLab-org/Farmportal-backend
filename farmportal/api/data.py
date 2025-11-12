# # apps/farmportal/farmportal/api/data.py
# import frappe
# from frappe import _

# @frappe.whitelist()
# def get_suppliers(search=None, limit=100):
#     """Public (logged-in) list of suppliers for the customer request dialog.
#        Adjust filters/fields to your needs.
#     """
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     filters = {}
#     if search:
#         # simple name filter (you can also add supplier_name like filters)
#         filters["name"] = ["like", f"%{search}%"]

#     rows = frappe.get_all(
#         "Supplier",
#         filters=filters,
#         fields=["name", "supplier_name"],
#         limit_page_length=min(int(limit or 100), 500),
#         order_by="supplier_name asc"
#     )

#     # Shape to what your UI expects
#     suppliers = [
#         {
#             "_id": r["name"],
#             "name": r["name"],
#             "companyName": r.get("supplier_name") or r["name"]
#         }
#         for r in rows
#     ]
#     return {"suppliers": suppliers}


import frappe
from frappe import _


@frappe.whitelist()
def get_suppliers(search=None, limit=100):
    """Get suppliers that have a linked user."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    # Build filters - only suppliers with custom_user field populated
    filters = {
        "disabled": 0,
        "custom_user": ["!=", ""]  # ✅ Changed from "user" to "custom_user"
    }
    
    # Handle search with OR condition
    or_filters = None
    if search:
        search_term = f"%{search}%"
        or_filters = [
            ["Supplier", "name", "like", search_term],
            ["Supplier", "supplier_name", "like", search_term]
        ]
    
    # Safe limit conversion
    try:
        page_limit = min(int(limit), 500) if limit else 100
    except (ValueError, TypeError):
        page_limit = 100
    
    # Query suppliers directly
    rows = frappe.get_all(
        "Supplier",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "supplier_name", "custom_user"],  # ✅ Changed field name
        limit_page_length=page_limit,
        order_by="supplier_name asc"
    )

    # Format response
    suppliers = [
        {
            "_id": r["name"],
            "name": r["name"],
            "companyName": r.get("supplier_name") or r["name"],
            "user": r.get("custom_user")  # ✅ Changed field name
        }
        for r in rows
    ]
    
    return {"suppliers": suppliers}
