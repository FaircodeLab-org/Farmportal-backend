import frappe, json
from frappe import _

# @frappe.whitelist(allow_guest=False)
# def get_profile_for_user():
#     """
#     Fetch Organization Module document linked to the logged-in user.
#     Returns full document JSON if found, else None.
#     """
#     user = frappe.session.user
#     existing = frappe.db.exists("Organization Module", {"user": user})
#     if not existing:
#         return None

#     doc = frappe.get_doc("Organization Module", existing)
#     return doc.as_dict()

@frappe.whitelist(allow_guest=False)
def get_profile_for_user():
    """
    Fetch Organization Module document linked to the logged-in user,
    including its certificate child records.
    """
    user = frappe.session.user
    existing = frappe.db.exists("Organization Module", {"user": user})
    if not existing:
        return None

    doc = frappe.get_doc("Organization Module", existing)

    # Return both organization info and certificates
    return {
        "name": doc.name,
        "organization_name": doc.organization_name,
        "website": doc.website,
        "phone": doc.phone,
        "street": doc.street,
        "house_no": doc.house_no,
        "postal_code": doc.postal_code,
        "city": doc.city,
        "country": doc.country,
        "type_of_market_operator": doc.type_of_market_operator,
        "logo": doc.logo,
        "user": doc.user,
        "certificates": [
            {
                "certificate_name": c.certificate_name,
                "evidence_type": c.evidence_type,
                "valid_from": c.valid_from,
                "valid_to": c.valid_to,
                "attachment": c.attachment,
            }
            for c in doc.get("certificates", [])
        ],
    }



@frappe.whitelist(methods=["POST"])
def save_profile(**payload):
    try:
        frappe.logger().info(f"Incoming payload: {payload}")
        data = frappe._dict(payload)

        if isinstance(data.get("data"), str):
            # Handle case where frontend sends JSON string inside 'data'
            import json
            data = frappe._dict(json.loads(data.get("data")))

        frappe.logger().info(f"Parsed data: {data}")

        if not data.get("organizationName"):
            frappe.throw("Organization Name is required")

        user = frappe.session.user
        frappe.logger().info(f"Session user: {user}")

        # Try to find existing doc for this user
        existing = frappe.db.exists("Organization Module", {"user": user})
        if existing:
            doc = frappe.get_doc("Organization Module", existing)
            doc.update(data)
            doc.save()
        else:
            doc = frappe.get_doc({
                "doctype": "Organization Module",
                "organization_name": data.organizationName,
                "user": user,
                **data
            }).insert()

        frappe.db.commit()
        return {"name": doc.name}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Organization Module Save Error")
        frappe.throw(str(e))



@frappe.whitelist(allow_guest=False)
def get_profile():
    """
    Fetch the Organization Module document linked to the current user.
    """
    user = frappe.session.user

    existing = frappe.db.exists("Organization Module", {"user": user})
    if not existing:
        return {"exists": False, "data": None}

    doc = frappe.get_doc("Organization Module", existing)
    return {
        "exists": True,
        "data": {
            "organization_name": doc.organization_name,
            "website": doc.website,
            "phone": doc.phone,
            "street": doc.street,
            "house_no": doc.house_no,
            "postal_code": doc.postal_code,
            "city": doc.city,
            "country": doc.country,
            "type_of_market_operator": doc.type_of_market_operator,
            "logo": doc.logo,
            "user": doc.user,
        }
    }





@frappe.whitelist(methods=["POST"])
def add_certificate(data: dict):
    """
    Add a certificate as a child record under Organization Module.
    """
    if isinstance(data, str):
        import json
        data = json.loads(data)

    profile_name = data.get("profileName")
    if not profile_name:
        frappe.throw(_("profileName (Organization Module) is required"))

    certificate_name = data.get("certificateName")
    if not certificate_name:
        frappe.throw(_("Certificate Name is required"))

    valid_from = data.get("validFrom")
    valid_to = data.get("validTo")
    if not (valid_from and valid_to):
        frappe.throw(_("Valid From and Valid To are required"))

    doc = frappe.get_doc("Organization Module", profile_name)
    doc.append("certificates", {
        "certificate_name": certificate_name,
        "evidence_type": data.get("evidenceType"),
        "valid_from": valid_from,
        "valid_to": valid_to,
        "attachment": data.get("fileUrl"),
    })
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {"message": "Certificate added successfully", "parent": doc.name}
    

@frappe.whitelist()
def delete_certificate(profile_name, certificate_name):
    profile = frappe.get_doc("Organization Module", profile_name)
    for cert in profile.get("certificates"):
        if cert.certificate_name == certificate_name:
            profile.remove(cert)
            profile.save(ignore_permissions=True)
            frappe.db.commit()
            return {"success": True, "message": f"Certificate '{certificate_name}' deleted"}
    frappe.throw(f"Certificate '{certificate_name}' not found")
