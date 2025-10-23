import frappe
from frappe import _

@frappe.whitelist(methods=["POST"])
def save_profile(**payload):
    """Create or update Organization Profile"""
    data = frappe._dict(payload)

    # Required field check
    if not data.name1:
        frappe.throw(_("Organization Name is required"))

    if data.get("name"):
        doc = frappe.get_doc("Organization Profile", data.name)
        doc.update(data)
        doc.save()
    else:
        doc = frappe.get_doc({
            "doctype": "Organization Profile",
            **data
        }).insert()

    frappe.db.commit()
    return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def add_certificate(profile_name, certificate_name, evidence_type=None,
                    valid_from=None, valid_to=None, file_url=None):
    """Attach a certificate to an existing profile"""
    doc = frappe.get_doc("Organization Profile", profile_name)

    row = doc.append("certificates", {
        "certificate_name": certificate_name,
        "evidence_type": evidence_type,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "file_url": file_url
    })
    doc.save()
    frappe.db.commit()

    return {"row_name": row.name, "file_url": file_url}
