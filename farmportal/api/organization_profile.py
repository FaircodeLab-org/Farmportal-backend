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

def _find_supplier_by_org_name(org_name):
    if not org_name:
        return None

    supplier_name = frappe.db.get_value("Supplier", {"supplier_name": org_name}, "name")
    if supplier_name:
        return supplier_name

    if frappe.db.exists("Supplier", org_name):
        return org_name

    return None


def _normalize_email(value):
    return (value or "").strip().lower()


def _resolve_user_name(value):
    if not value:
        return None

    raw_value = value.strip()
    if frappe.db.exists("User", raw_value):
        return raw_value

    user_from_username = frappe.db.get_value("User", {"username": raw_value}, "name")
    if user_from_username:
        return user_from_username

    email_norm = _normalize_email(raw_value)
    if not email_norm:
        return None

    if frappe.db.exists("User", email_norm):
        return email_norm

    user_from_username = frappe.db.get_value("User", {"username": email_norm}, "name")
    if user_from_username:
        return user_from_username

    return frappe.db.get_value("User", {"email": email_norm}, "name")


def _get_supplier_for_user(user, supplier_hint=None):
    if supplier_hint:
        if frappe.db.exists("Supplier", supplier_hint):
            return supplier_hint

        org_name = frappe.db.get_value("Organization Module", supplier_hint, "organization_name")
        supplier_from_org = _find_supplier_by_org_name(org_name)
        if supplier_from_org:
            return supplier_from_org

        supplier_from_hint = _find_supplier_by_org_name(supplier_hint)
        if supplier_from_hint:
            return supplier_from_hint

    supplier_name = frappe.db.get_value("Supplier", {"custom_user": user}, "name")
    if supplier_name:
        return supplier_name

    if frappe.db.exists("Supplier", user):
        return user

    org_name = frappe.db.get_value("Organization Module", {"user": user}, "organization_name")
    supplier_from_org = _find_supplier_by_org_name(org_name)
    if supplier_from_org:
        return supplier_from_org

    return None


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

    supplier_members = []
    supplier_name = _get_supplier_for_user(user)
    if supplier_name:
        supplier_doc = frappe.get_doc("Supplier", supplier_name)
        supplier_members = [
            {
                "name": m.name,
                "first_name": m.first_name,
                "last_name": m.last_name,
                "email": m.email,
                "designation": m.designation,
                "user_link": m.user_link,
            }
            for m in supplier_doc.get("custom_organization_members", [])
        ]

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
        "custom_organization_members": supplier_members,
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
            doc.save(ignore_permissions=True)
        else:
            doc = frappe.get_doc({
                "doctype": "Organization Module",
                "organization_name": data.organizationName,
                "user": user,
                **data
            }).insert(ignore_permissions=True)

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




def manage_organization_users(doc, method):
    """
    Syncs the custom organization members child table with System Users.
    Run on Supplier.validate
    """
    if not hasattr(doc, "custom_organization_members"):
        return

    for member in doc.get("custom_organization_members"):
        if not member.email:
            continue

        # Check if User exists
        if not frappe.db.exists("User", member.email):
            # 1. Create New User
            user = frappe.get_doc({
                "doctype": "User",
                "email": member.email,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "enabled": 1,
                "send_welcome_email": 1,
                "roles": [{"role": "Supplier"}] 
            })
            user.insert(ignore_permissions=True)
            
            # 2. Link User ID back to the child table row
            member.user_link = user.name
            
            # 3. Ensure Contact Exists (Vital for permissions)
            create_contact_link(user, member, doc.name)
        
        else:
            # User exists, ensure link is set
            if not member.user_link:
                member.user_link = member.email 
                # Still ensure contact exists even if user existed before
                user_doc = frappe.get_doc("User", member.email)
                create_contact_link(user_doc, member, doc.name)

def create_contact_link(user, member, supplier_name):
    """
    Ensures a Contact exists linking this User to this Supplier.
    """
    contact_name = frappe.db.get_value("Contact", {"email_id": user.email})
    
    if not contact_name:
        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": member.first_name,
            "last_name": member.last_name,
            "email_id": user.email,
            "user": user.name,
            "links": [{"link_doctype": "Supplier", "link_name": supplier_name}]
        })
        contact.insert(ignore_permissions=True)
    else:
        # Check if already linked to THIS supplier
        contact = frappe.get_doc("Contact", contact_name)
        is_linked = any(l.link_name == supplier_name and l.link_doctype == 'Supplier' for l in contact.links)
        
        if not is_linked:
            contact.append("links", {
                "link_doctype": "Supplier",
                "link_name": supplier_name
            })
            contact.save(ignore_permissions=True)
            
            
@frappe.whitelist(methods=["POST"])
def add_member(**kwargs):
    try:
        # 1. Parse Payload
        data = kwargs.get('data')
        if data is None: data = kwargs
        if isinstance(data, str): import json; data = json.loads(data)

        # 2. Validate Inputs
        email = (data.get("email") or "").strip()
        if not email: frappe.throw("Email is required")
        email_norm = _normalize_email(email)
        
        # 3. FIND THE SUPPLIER
        # We ignore 'supplierName' from frontend because it might be the Org Module ID.
        # Instead, we reliably find the Supplier linked to the *current logged-in user*.
        
        user = frappe.session.user
        supplier_hint = data.get("supplierName") or data.get("organizationName") or data.get("organization_name")
        supplier_name = _get_supplier_for_user(user, supplier_hint)
        
        if not supplier_name:
             frappe.throw("No Supplier account found linked to this user.")

        # 4. Get the Supplier Document
        supplier_doc = frappe.get_doc("Supplier", supplier_name)
        
        # 5. Add to custom child table
        existing_members = supplier_doc.get("custom_organization_members") or []
        
        for member in existing_members:
            if _normalize_email(member.email) == email_norm:
                frappe.throw(f"Member {email} already exists")

        supplier_doc.append("custom_organization_members", {
            "first_name": data.get("firstName"),
            "last_name": data.get("lastName"),
            "email": email,
            "designation": data.get("designation") or data.get("deisgnation")
        })
        
        supplier_doc.save(ignore_permissions=True) # This triggers the hooks we wrote earlier!
        frappe.db.commit()
        
        return {"message": "Member added to Supplier"}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Add Member Error")
        frappe.throw(str(e))



@frappe.whitelist(methods=["POST"])
def remove_member(**kwargs):
    try:
        # Flexible payload parsing
        data = kwargs.get('data')
        if data is None: data = kwargs
        if isinstance(data, str): import json; data = json.loads(data)

        email = (data.get("email") or "").strip()
        member_id = data.get("memberId") or data.get("member_id") or data.get("memberName")
        
        if not email and not member_id:
            frappe.throw(_("Email or memberId is required"))
        email_norm = _normalize_email(email)

        supplier_hint = data.get("supplierName") or data.get("organizationName") or data.get("organization_name")
        supplier_name = _get_supplier_for_user(frappe.session.user, supplier_hint)
        if not supplier_name:
            frappe.throw("No Supplier account found linked to this user.")

        doc = frappe.get_doc("Supplier", supplier_name)
        
        members_list = doc.get("custom_organization_members") or []
        rows_to_remove = []

        if member_id:
            rows_to_remove = [row for row in members_list if row.name == member_id]

        if not rows_to_remove and email_norm:
            rows_to_remove = [
                row for row in members_list
                if _normalize_email(row.email) == email_norm
                or _normalize_email(getattr(row, "user_link", "")) == email_norm
                or _normalize_email(getattr(row, "user", "")) == email_norm
            ]

        if not rows_to_remove:
            frappe.throw(_("Member not found"))

        user_ids_to_disable = set()
        for row in rows_to_remove:
            for candidate in (getattr(row, "user_link", None), getattr(row, "user", None), row.email):
                resolved = _resolve_user_name(candidate)
                if resolved:
                    user_ids_to_disable.add(resolved)
            doc.remove(row)
            
        doc.save(ignore_permissions=True)
        frappe.db.commit() # Commit the changes
        
        # Optional: Disable the user account(s)
        if email_norm:
            resolved_from_payload = _resolve_user_name(email_norm)
            if resolved_from_payload:
                user_ids_to_disable.add(resolved_from_payload)

        disabled_users = []
        if user_ids_to_disable:
            for user_id in user_ids_to_disable:
                try:
                    if user_id in ("Administrator", "Guest"):
                        continue
                    if frappe.db.exists("User", user_id):
                        frappe.db.set_value("User", user_id, "enabled", 0, update_modified=False)
                        disabled_users.append(user_id)
                except Exception:
                    frappe.log_error(frappe.get_traceback(), "Disable User Error (remove_member)")

            frappe.cache.delete_key("enabled_users")
            frappe.db.commit()

        return {"message": "Member removed successfully", "disabled_users": disabled_users}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Remove Member Error")
        frappe.throw(str(e))
