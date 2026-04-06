import frappe


def _normalize_verification_status(value):
    raw = str(value or "").strip().lower()
    if raw in {"verified", "verify", "approved", "done", "complete", "completed"}:
        return "Verified"
    if raw in {"rejected", "reject", "declined"}:
        return "Rejected"
    return "Pending"


def _supplier_verification_key(supplier_name):
    return f"supplier_verification_status::{str(supplier_name or '').strip()}"


def _get_supplier_verification_status(supplier_name):
    supplier_name = str(supplier_name or "").strip()
    if not supplier_name:
        return "Pending"

    value = None
    try:
        meta = frappe.get_meta("Supplier")
        for fieldname in ("custom_verification_status", "verification_status"):
            if meta.has_field(fieldname):
                value = frappe.db.get_value("Supplier", supplier_name, fieldname)
                break
    except Exception:
        value = None

    if value is None or str(value).strip() == "":
        value = frappe.defaults.get_global_default(_supplier_verification_key(supplier_name))

    return _normalize_verification_status(value)


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
    verification_status = _get_supplier_verification_status(
        supplier.get("name") if isinstance(supplier, dict) else None
    )

    return {
        "user": {
            "name": user_doc.name,
            "full_name": user_doc.full_name,
            "email": user_doc.email,
            "roles": roles,
        },
        "employee": employee,
        "supplier": supplier,
        "verification_status": verification_status,
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
    for fieldname in ("custom_user", "user_id", "user"):
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

    # Try Supplier User child table membership
    try:
        child_meta = frappe.get_meta("Supplier User")
        clauses = []
        params = []

        user_norm = (user_doc.name or "").strip().lower()
        email_norm = (user_doc.email or "").strip().lower()

        if child_meta.has_field("user_link") and user_norm:
            clauses.append("LOWER(COALESCE(`user_link`, '')) = %s")
            params.append(user_norm)
        if child_meta.has_field("user") and user_norm:
            clauses.append("LOWER(COALESCE(`user`, '')) = %s")
            params.append(user_norm)
        if child_meta.has_field("email") and email_norm:
            clauses.append("LOWER(COALESCE(`email`, '')) = %s")
            params.append(email_norm)

        if clauses:
            rows = frappe.db.sql(
                f"""
                SELECT parent
                FROM `tabSupplier User`
                WHERE parenttype = 'Supplier'
                  AND ({' OR '.join(clauses)})
                ORDER BY modified DESC
                LIMIT 1
                """,
                tuple(params),
                as_dict=True,
            )
            if rows:
                supplier_name = rows[0].get("parent")
                if supplier_name:
                    sup = frappe.db.get_value(
                        "Supplier",
                        supplier_name,
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
