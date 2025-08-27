# apps/farmportal/farmportal/api/data.py
import frappe
from frappe import _

@frappe.whitelist()
def get_suppliers(search=None, limit=100):
    """Public (logged-in) list of suppliers for the customer request dialog.
       Adjust filters/fields to your needs.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    filters = {}
    if search:
        # simple name filter (you can also add supplier_name like filters)
        filters["name"] = ["like", f"%{search}%"]

    rows = frappe.get_all(
        "Supplier",
        filters=filters,
        fields=["name", "supplier_name"],
        limit_page_length=min(int(limit or 100), 500),
        order_by="supplier_name asc"
    )

    # Shape to what your UI expects
    suppliers = [
        {
            "_id": r["name"],
            "name": r["name"],
            "companyName": r.get("supplier_name") or r["name"]
        }
        for r in rows
    ]
    return {"suppliers": suppliers}
