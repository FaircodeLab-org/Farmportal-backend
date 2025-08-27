import json
import frappe
from frappe import _

DT = "Update profile"

def _payload_from_request(data=None):
    """Accepts JSON string/dict, or reads from request body/form."""
    if data is not None:
        if isinstance(data, str):
            return json.loads(data)
        return data

    # Try form first (e.g., data=<json-string>)
    if frappe.form_dict and frappe.form_dict.get("data"):
        try:
            return json.loads(frappe.form_dict.get("data"))
        except Exception:
            # if it's already a dict-like, return as-is
            return frappe.form_dict.get("data")

    # Then raw JSON body
    try:
        body = frappe.request.get_json(silent=True)
        if isinstance(body, dict):
            return body
    except Exception:
        pass

    return {}

def _safe_set(doc, fieldname, value):
    if value is None:
        return
    if doc.meta.get_field(fieldname):
        doc.set(fieldname, value)

@frappe.whitelist()
def get_profile():
    """Return profile for the logged-in user ({} if none)."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    name = frappe.db.get_value(DT, {"user": user})
    if not name:
        return {}

    doc = frappe.get_doc(DT, name)  # read full doc and map to API shape
    # Use getattr with defaults so missing fields don't explode
    return {
        "companyName": getattr(doc, "company_name", "") or "",
        "contactPerson": {
            "name": getattr(doc, "contact_person_name", "") or "",
            "phone": getattr(doc, "contact_person_phone", "") or "",
            "position": getattr(doc, "contact_person_position", "") or "",
        },
        "address": {
            "street": getattr(doc, "address_street", "") or "",
            "city": getattr(doc, "address_city", "") or "",
            "state": getattr(doc, "address_state", "") or "",
            "postalCode": getattr(doc, "address_postal_code", "") or "",
        },
    }

@frappe.whitelist()
def update_profile(data=None):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    payload = _payload_from_request(data) or {}

    name = frappe.db.get_value(DT, {"user": user})
    if name:
        doc = frappe.get_doc(DT, name)
    else:
        doc = frappe.new_doc(DT)
        _safe_set(doc, "user", user)

    _safe_set(doc, "company_name", payload.get("companyName"))

    cp = payload.get("contactPerson") or {}
    _safe_set(doc, "contact_person_name", cp.get("name"))
    _safe_set(doc, "contact_person_phone", cp.get("phone"))
    _safe_set(doc, "contact_person_position", cp.get("position"))

    addr = payload.get("address") or {}
    _safe_set(doc, "address_street", addr.get("street"))
    _safe_set(doc, "address_city", addr.get("city"))
    _safe_set(doc, "address_state", addr.get("state"))
    _safe_set(doc, "address_postal_code", addr.get("postalCode"))

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": _("Profile updated successfully"), "name": doc.name}

    # except Exception as e:
    #     # capture the traceback in Error Log for quick diagnosis
    #     frappe.log_error(frappe.get_traceback(), "Update Profile API Error")
    #     # return a readable error to the client
    #     frappe.throw(_("Could not update profile: {0}").format(str(e)))
