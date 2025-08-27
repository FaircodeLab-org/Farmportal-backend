# apps/farmportal/farmportal/api/requests.py

import json
import frappe
from frappe import _

DT = "Request"

# NEW: preferred user link fields per doctype (ordered by priority)
USER_LINK_FIELDS = {
    "Customer": ["custom_user", "user_id", "user"],
    "Supplier": ["custom_user", "user_id", "user"],
}

def _as_list(val):
    if not val:
        return []
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return []
    return val if isinstance(val, list) else []

def _get_user_email(user: str) -> str | None:
    try:
        return frappe.db.get_value("User", user, "email")
    except Exception:
        return None

def _link_by_contact_email(user: str, target_doctype: str) -> str | None:
    """Fallback: User -> Contact (by email) -> Dynamic Link -> (Customer/Supplier)."""
    email = _get_user_email(user)
    if not email:
        return None

    contacts = frappe.get_all("Contact Email", filters={"email_id": email}, fields=["parent"])
    if not contacts:
        return None
    contact_names = [c["parent"] for c in contacts]

    dl = frappe.get_all(
        "Dynamic Link",
        filters={
            "parenttype": "Contact",
            "parent": ["in", contact_names],
            "link_doctype": target_doctype,
        },
        fields=["link_name"],
        limit=1,
    )
    return dl[0]["link_name"] if dl else None

def _link_by_user_field(doctype: str, user: str) -> str | None:
    """
    Try mapping via a Link field on the target doctype that points to User.
    Priority defined in USER_LINK_FIELDS.
    """
    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return None

    for fieldname in USER_LINK_FIELDS.get(doctype, []):
        if meta.has_field(fieldname):
            name = frappe.db.get_value(doctype, {fieldname: user}, "name")
            if name:
                return name
    return None

def _get_party_from_user(user: str) -> tuple[str | None, str | None]:
    """
    Resolve (customer_name, supplier_name) for this User.
    1) Try custom_user/user_id/user on the target doctype
    2) Fallback via Contact email -> Dynamic Link
    """
    customer = _link_by_user_field("Customer", user) or _link_by_contact_email(user, "Customer")
    supplier = _link_by_user_field("Supplier", user) or _link_by_contact_email(user, "Supplier")
    return customer, supplier

# (the rest of your file: get_customer_requests, get_supplier_requests,
#  create_request, respond_to_request) stays the same


@frappe.whitelist()
def get_customer_requests():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    try:
        customer, supplier = _get_party_from_user(user)
        # Two-type rule: Supplier shouldn't see the customer endpoint
        if supplier and not customer:
            return {"requests": []}
        if not customer:
            # No mapping found; don't crash—return empty
            return {"requests": []}

        rows = frappe.get_all(
            DT,
            filters={"customer": customer},
            # fields=[
            #     "name as id", "status", "request_type", "message",
            #     "customer", "supplier", "creation", "modified"
            # ],
            fields=[
                "name as id", "status", "request_type", "message",
                "customer", "supplier", "response_message",   # <— add this
                "creation", "modified"
            ],
            order_by="creation desc",
            limit_page_length=200
        )
        for r in rows:
            r["customer_info"] = {"name": r.get("customer")}
            r["supplier_info"] = {"name": r.get("supplier")}
        return {"requests": rows}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "get_customer_requests error")
        return {"requests": []}

@frappe.whitelist()
def get_supplier_requests():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    try:
        customer, supplier = _get_party_from_user(user)
        if not supplier:
            return {"requests": []}

        rows = frappe.get_all(
            DT,
            filters={"supplier": supplier},
            # fields=[
            #     "name as id", "status", "request_type", "message",
            #     "customer", "supplier", "creation", "modified"
            # ],
            fields=[
                "name as id", "status", "request_type", "message",
                "customer", "supplier", "response_message",   # <— add this
                "creation", "modified"
            ],
            order_by="creation desc",
            limit_page_length=200
        )
        for r in rows:
            r["customer_info"] = {"name": r.get("customer")}
            r["supplier_info"] = {"name": r.get("supplier")}
        return {"requests": rows}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "get_supplier_requests error")
        return {"requests": []}

@frappe.whitelist()
def create_request(
    supplier_id: str,
    request_type: str,
    message: str | None = None,
    requested_products: list[dict] | str | None = None,
    customer_id: str | None = None,  # <-- optional explicit override
):
    """Customer-side: create a Request to a Supplier."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier_flag = _get_party_from_user(user)
    # Two-type rule: a true Supplier shouldn't be able to create customer requests
    if supplier_flag and not customer and not customer_id:
        frappe.throw(_("Suppliers cannot create requests"), frappe.PermissionError)

    # Allow explicit customer override if you pass it from the client
    if customer_id:
        customer = customer_id

    if not customer:
        frappe.throw(_("No Customer linked to your user"), frappe.PermissionError)

    doc = frappe.new_doc(DT)
    doc.customer = customer
    doc.supplier = supplier_id
    doc.request_type = request_type
    doc.message = message
    doc.requested_by = user
    doc.status = "Pending"

    items = _as_list(requested_products)
    if items and doc.meta.get_field("requested_products"):
        for it in items:
            row = doc.append("requested_products", {})
            row.item_code = it.get("item_code")
            row.qty = it.get("qty")
            row.uom = it.get("uom")

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"name": doc.name, "message": _("Request created")}

# @frappe.whitelist()
# def respond_to_request(request_id, action=None, message=None, shared_plots=None, status=None):
#     """Supplier-side: respond to a Request."""
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     customer, supplier = _get_party_from_user(user)
#     if not supplier:
#         frappe.throw(_("Only Suppliers can respond"), frappe.PermissionError)

#     doc = frappe.get_doc(DT, request_id)

#     if doc.supplier != supplier:
#         frappe.throw(_("Not permitted to respond to this request"), frappe.PermissionError)

#     final_status = (status or "").strip().lower()
#     if action:
#         act = action.strip().lower()
#         if act == "accept":
#             final_status = "completed"
#         elif act == "reject":
#             final_status = "rejected"

#     if final_status in ("completed", "rejected"):
#         doc.status = final_status.capitalize()

#     if message:
#         doc.response_message = message

#     if shared_plots:
#         try:
#             as_json = json.dumps(shared_plots) if not isinstance(shared_plots, str) else shared_plots
#             doc.shared_plots_json = as_json
#         except Exception:
#             pass

#     doc.responded_by = user
#     doc.save(ignore_permissions=True)
#     frappe.db.commit()
#     return {"message": _("Response saved"), "status": doc.status}

# @frappe.whitelist()
# def respond_to_request(request_id, action=None, message=None, shared_plots=None, status=None):
#     """Supplier-side: respond to a Request."""
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     customer, supplier = _get_party_from_user(user)
#     if not supplier:
#         frappe.throw(_("Only Suppliers can respond"), frappe.PermissionError)

#     doc = frappe.get_doc(DT, request_id)

#     if doc.supplier != supplier:
#         frappe.throw(_("Not permitted to respond to this request"), frappe.PermissionError)

#     # --- Normalize action/status very liberally ---
#     s = (status or "").strip().lower()
#     a = (action or "").strip().lower()

#     print(a, s)

#     # map many variants to final statuses
#     if a in {"accepted", "approved", "approve", "ok"}:
#         s = "accepted"
#     elif a in {"reject", "decline", "declined", "no"}:
#         s = "rejected"

#     if s in {"completed", "complete", "accepted", "accept"}:
#         doc.status = "Completed"
#     elif s in {"rejected", "reject"}:
#         doc.status = "Rejected"
#     # else: leave as-is (e.g., Pending) if nothing matched

#     if message is not None:
#         doc.response_message = message

#     if shared_plots:
#         try:
#             as_json = json.dumps(shared_plots) if not isinstance(shared_plots, str) else shared_plots
#             doc.shared_plots_json = as_json
#         except Exception:
#             pass

#     doc.responded_by = user
#     doc.save(ignore_permissions=True)
#     frappe.db.commit()

#     # Return fresh, useful fields so UI can update instantly
#     return {
#         "id": doc.name,
#         "status": doc.status,
#         "response_message": doc.response_message,
#         "customer": doc.customer,
#         "supplier": doc.supplier,
#         "message": _("Response saved"),
#     }


@frappe.whitelist()
def respond_to_request(request_id, action=None, message=None, shared_plots=None, status=None):
    """Supplier-side: respond to a Request."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier = _get_party_from_user(user)
    if not supplier:
        frappe.throw(_("Only Suppliers can respond"), frappe.PermissionError)

    doc = frappe.get_doc(DT, request_id)

    if doc.supplier != supplier:
        frappe.throw(_("Not permitted to respond to this request"), frappe.PermissionError)

    # --- Normalize inputs ---
    a = (action or "").strip().lower()
    s = (status or "").strip().lower()

    # Accept / reject synonyms (cover both action and status)
    ACCEPT = {"accept", "accepted", "approve", "approved", "ok", "yes", "y", "complete", "completed", "done"}
    REJECT = {"reject", "rejected", "decline", "declined", "no", "n"}

    # Pick a single token to decide with
    token = a or s  # prefer explicit action, else status

    if token in ACCEPT:
        doc.status = "Completed"
    elif token in REJECT:
        doc.status = "Rejected"
    # else: leave doc.status as-is (e.g., Pending) if nothing matched

    if message is not None:
        doc.response_message = message

    if shared_plots:
        try:
            as_json = json.dumps(shared_plots) if not isinstance(shared_plots, str) else shared_plots
            doc.shared_plots_json = as_json
        except Exception:
            pass

    doc.responded_by = user
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Return fresh fields for optimistic UI update
    return {
        "id": doc.name,
        "status": doc.status,
        "response_message": doc.response_message,
        "customer": doc.customer,
        "supplier": doc.supplier,
        "message": _("Response saved"),
    }
