import frappe
from frappe import _

@frappe.whitelist()
def create_supplier_with_user(name, email, country=None):
    """
    Creates a User, then a Supplier linked to that User, and sends a welcome email.
    """
    # 1. Validation
    if not name or not email:
        frappe.throw(_("Name and Email are required"))

    if frappe.db.exists("User", email):
        frappe.throw(_("A user with email {0} already exists").format(email))

    try:
        # 2. Create User
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": name,
            "enabled": 1,
            "send_welcome_email": 1, # This triggers the standard welcome mail
            "roles": [{"role": "Supplier"}] # Assign Supplier Role
        })
        user.insert(ignore_permissions=True)

        # 3. Create Supplier
        supplier = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": name,
            "country": country,
            "supplier_group": "All Supplier Groups", # Default required field
            "custom_user": user.name # Link the created user
        })
        supplier.insert(ignore_permissions=True)

        # 4. Commit
        frappe.db.commit()

        return {
            "message": "Supplier and User created successfully",
            "supplier": supplier.name,
            "user": user.name
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Supplier Creation Error: {str(e)}")
        frappe.throw(_("Failed to create supplier: {0}").format(str(e)))
        

@frappe.whitelist()
def toggle_supplier_access(supplier_name, enable=0):
    """
    Disables or Enables the User linked to the Supplier.
    enable: 0 to disable, 1 to enable
    """
    if not supplier_name:
        frappe.throw(_("Supplier Name is required"))

    supplier = frappe.get_doc("Supplier", supplier_name)
    
    if not supplier.custom_user:
        frappe.throw(_("This supplier is not linked to a User account"))

    user = frappe.get_doc("User", supplier.custom_user)
    
    # Toggle enabled status
    user.enabled = int(enable)
    user.save(ignore_permissions=True)
    frappe.db.commit()

    status = "Enabled" if user.enabled else "Disabled"
    return {"message": f"Supplier access {status}", "enabled": user.enabled}


@frappe.whitelist()
def get_suppliers(search=None, limit=100):
    """
    Get suppliers linked to a User, including their email and enabled status.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    # Safe limit
    try:
        page_limit = min(int(limit), 500) if limit else 100
    except (ValueError, TypeError):
        page_limit = 100

    # Prepare search condition
    search_condition = ""
    params = {}
    if search:
        search_condition = """
            AND (
                s.supplier_name LIKE %(search)s 
                OR s.name LIKE %(search)s
                OR u.email LIKE %(search)s
            )
        """
        params["search"] = f"%{search}%"

    # SQL Query with Join to get User details (email, enabled status)
    # We filter by s.disabled = 0 (Supplier doctype status)
    # We DO NOT filter by u.enabled so we can see disabled users in the list
    query = f"""
        SELECT 
            s.name, 
            s.supplier_name, 
            s.country, 
            s.custom_user,
            u.email, 
            u.enabled as user_enabled
        FROM `tabSupplier` s
        JOIN `tabUser` u ON s.custom_user = u.name
        WHERE 
            s.disabled = 0
            AND s.custom_user IS NOT NULL 
            AND s.custom_user != ''
            {search_condition}
        ORDER BY s.supplier_name ASC
        LIMIT {page_limit}
    """

    data = frappe.db.sql(query, params, as_dict=True)

    # Format response for frontend
    suppliers = [
        {
            "_id": row.name,
            "name": row.name,
            "supplier_name": row.supplier_name or row.name, # Display name
            "country": row.country,
            "user": row.custom_user,
            "email_id": row.email,          # For displaying contact email
            "user_enabled": row.user_enabled # 1 or 0
        }
        for row in data
    ]
    
    return {"suppliers": suppliers}