import frappe
from frappe import _

# @frappe.whitelist(methods=["POST"])
# def save_profile(**payload):
#     """Create or update Organization Profile"""
#     data = frappe._dict(payload)

#     # Required field check
#     if not data.name1:
#         frappe.throw(_("Organization Name is required"))

#     if data.get("name"):
#         doc = frappe.get_doc("Organization Profile", data.name)
#         doc.update(data)
#         doc.save()
#     else:
#         doc = frappe.get_doc({
#             "doctype": "Organization Profile",
#             **data
#         }).insert()

#     frappe.db.commit()
#     return {"name": doc.name}


# @frappe.whitelist(methods=["POST"])
# def add_certificate(profile_name, certificate_name, evidence_type=None,
#                     valid_from=None, valid_to=None, file_url=None):
#     """Attach a certificate to an existing profile"""
#     doc = frappe.get_doc("Organization Profile", profile_name)

#     row = doc.append("certificates", {
#         "certificate_name": certificate_name,
#         "evidence_type": evidence_type,
#         "valid_from": valid_from,
#         "valid_to": valid_to,
#         "file_url": file_url
#     })
#     doc.save()
#     frappe.db.commit()

#     return {"row_name": row.name, "file_url": file_url}
# organization_profile.py

@frappe.whitelist(methods=["POST"])
def save_profile(**payload):
    data = frappe._dict(payload)

    # Map UI key to DocType field BEFORE validation
    if data.get("organizationName") and not data.get("name1"):
        data.name1 = data.organizationName

    # Required field check
    if not data.get("name1"):
        frappe.throw(_("Organization Name is required"))

    if data.get("name"):
        if not frappe.db.exists("Organization Profile", data.name):
            frappe.throw(_("Organization Profile {0} not found").format(data.name))
        doc = frappe.get_doc("Organization Profile", data.name)
        doc.update(data)
        doc.save()
    else:
        doc = frappe.get_doc({ "doctype": "Organization Profile", **data }).insert()

    return {"name": doc.name}




@frappe.whitelist(methods=["POST"])
def add_certificate(profile_name, certificate_name, evidence_type=None,
                    valid_from=None, valid_to=None, file_url=None):
    """Attach a certificate to an existing profile"""
    if not profile_name:
        frappe.throw(_("profile_name is required"))
    if not certificate_name:
        frappe.throw(_("certificate_name is required"))

    # Date sanity (optional but recommended)
    if valid_from and valid_to:
        try:
            from frappe.utils import getdate
            if getdate(valid_from) > getdate(valid_to):
                frappe.throw(_("Valid From must be earlier than or equal to Valid To"))
        except Exception:
            frappe.throw(_("Invalid date format for valid_from/valid_to"))

    # Ensure parent exists
    if not frappe.db.exists("Organization Profile", profile_name):
        frappe.throw(_("Organization Profile {0} not found").format(profile_name))

    try:
        doc = frappe.get_doc("Organization Profile", profile_name)
        row = doc.append("certificates", {
            "certificate_name": certificate_name,
            "evidence_type": evidence_type,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "file_url": file_url
        })
        doc.save()
        # Optional: frappe.db.commit()
        return {"row_name": row.name, "file_url": file_url}
    except frappe.ValidationError:
        # Pass-through child row validation to client
        frappe.local.response["http_status_code"] = 422
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "add_certificate_error")
        frappe.throw(_("Failed to add certificate: {0}").format(str(e)))
