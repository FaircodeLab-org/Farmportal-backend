import frappe

@frappe.whitelist()
def me():
    """Return info about the currently logged-in user, roles, and linked Employee/Supplier."""
    user_id = frappe.session.user
    if user_id in ("Guest", None):
        frappe.throw("Not logged in", frappe.PermissionError)

    user_doc = frappe.get_doc("User", user_id)
    roles = [r.role for r in user_doc.roles]

    employee = get_employee_for_user(user_id)
    supplier = get_supplier_for_user(user_doc)  # note: pass full doc for email

    return {
        "user": {
            "name": user_doc.name,
            "full_name": user_doc.full_name,
            "email": user_doc.email,
            "roles": roles,
        },
        "employee": employee,   # None or { name, employee_name }
        "supplier": supplier,   # None or { name, supplier_name }
    }


def get_employee_for_user(user_id: str):
    """Standard ERPNext link: Employee.user_id -> User.name"""
    return frappe.db.get_value(
        "Employee",
        {"user_id": user_id},
        ["name", "employee_name"],
        as_dict=True
    )


def get_supplier_for_user(user_doc):
    """Find Supplier for a user via:
       1) Custom link fields on Supplier if present (user_id / user),
       2) Otherwise via Contact(email_id == user.email) -> Dynamic Link(link_doctype='Supplier')."""
    # 1) CUSTOM FIELD FALLBACKS (use if you created such a field)
    # Try common custom field names safely (no crash if field doesn't exist)
    for fieldname in ("user_id", "user"):
        try:
            sup = frappe.db.get_value(
                "Supplier",
                {fieldname: user_doc.name},
                ["name", "supplier_name"],
                as_dict=True,
            )
            if sup:
                return sup
        except Exception:
            # Field likely doesn't exist; just skip to next method
            pass

    # 2) STANDARD ERPNext: Contact(email) -> Dynamic Link -> Supplier
    if not user_doc.email:
        return None

    # Find contacts with this email
    contact_names = frappe.get_all(
        "Contact",
        filters={"email_id": user_doc.email},
        pluck="name",
        limit=10
    )

    if not contact_names:
        return None

    # Find any Dynamic Link from those contacts pointing to Supplier
    link = frappe.get_all(
        "Dynamic Link",
        filters={
            "parent": ["in", contact_names],
            "link_doctype": "Supplier",
        },
        fields=["link_name"],
        limit=1,
    )

    if not link:
        return None

    supplier_name = link[0].link_name
    return frappe.db.get_value(
        "Supplier",
        supplier_name,
        ["name", "supplier_name"],
        as_dict=True
    )
import frappe

@frappe.whitelist()
def get_customer_requests():
    """Return a simple list of requests for a 'customer' user.
    Adjust the DocType and filters to your actual schema."""
    user = frappe.session.user
    if user in ("Guest", None):
        frappe.throw("Not logged in", frappe.PermissionError)

    # Try common doctypes; fall back gracefully if they don't exist.
    doctype = None
    for dt in ("Customer Request", "Request"):
        if frappe.db.exists("DocType", dt):
            doctype = dt
            break

    if not doctype:
        return {"items": []}

    # Example filter: owned by the user. Change to your model (e.g. requester, customer, etc.)
    rows = frappe.get_all(
        doctype,
        filters={"owner": user},
        fields=["name", "status", "subject", "creation"],
        order_by="creation desc",
        limit_page_length=200,
    )
    return {"items": rows}


@frappe.whitelist()
def get_supplier_requests():
    """Return requests assigned to a supplier (logged-in user).
    Adjust filters to match your schema."""
    user = frappe.session.user
    if user in ("Guest", None):
        frappe.throw("Not logged in", frappe.PermissionError)

    doctype = None
    for dt in ("Supplier Request", "Customer Request", "Request"):
        if frappe.db.exists("DocType", dt):
            doctype = dt
            break

    if not doctype:
        return {"items": []}

    # Example filters: assigned_to == user or owner == user; tweak as needed.
    rows = frappe.get_all(
        doctype,
        filters=[["owner", "=", user]],  # or ["assigned_to","=",user] if you track assignment
        fields=["name", "status", "subject", "creation"],
        order_by="creation desc",
        limit_page_length=200,
    )
    return {"items": rows}


