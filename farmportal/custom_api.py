import frappe

@frappe.whitelist()
def get_current_user():
    """Return info about the currently logged-in user, roles, and linked Employee/Supplier."""
    user_id = frappe.session.user
    if user_id in ("Guest", None):
        frappe.throw("Not logged in", frappe.PermissionError)

    user_doc = frappe.get_doc("User", user_id)
    roles = [r.role for r in user_doc.roles]

    employee = get_employee_for_user(user_id)
    supplier = get_supplier_for_user(user_doc)

    return {
        "user": {
            "name": user_doc.name,
            "full_name": user_doc.full_name,
            "email": user_doc.email,
            "roles": roles,
        },
        "employee": employee,
        "supplier": supplier,
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
    """Find Supplier for a user via custom fields or Contact linkage"""
    # Try custom field approach first
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
            pass

    # Standard ERPNext: Contact -> Dynamic Link -> Supplier
    if not user_doc.email:
        return None

    contact_names = frappe.get_all(
        "Contact",
        filters={"email_id": user_doc.email},
        pluck="name",
        limit=10
    )

    if not contact_names:
        return None

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