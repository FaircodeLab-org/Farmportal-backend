import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def login_and_get_api_keys(usr, pwd):
    """
    Authenticate user with email/password and return API keys.
    Automatically generates keys if they don't exist.
    """
    try:
        # Authenticate the user
        frappe.local.login_manager.authenticate(usr, pwd)
        frappe.local.login_manager.post_login()
        
        user = frappe.session.user
        
        if user == "Guest":
            frappe.throw(_("Invalid credentials"), frappe.AuthenticationError)
        
        # Get user document
        user_doc = frappe.get_doc("User", user)
        
        # Check if API keys exist, if not generate them
        api_key = user_doc.api_key
        api_secret = None
        
        if api_key:
            # Try to get existing secret
            try:
                api_secret = user_doc.get_password('api_secret')
            except:
                api_secret = None
        
        # If no keys exist or secret is missing, generate new ones
        if not api_key or not api_secret:
            api_key = frappe.generate_hash(length=15)
            api_secret = frappe.generate_hash(length=15)
            
            user_doc.api_key = api_key
            user_doc.api_secret = api_secret
            user_doc.save(ignore_permissions=True)
            frappe.db.commit()
        
        # Get user details
        return {
            "success": True,
            "api_key": api_key,
            "api_secret": api_secret,
            "user": {
                "name": user_doc.name,
                "full_name": user_doc.full_name,
                "email": user_doc.email,
            }
        }
        
    except frappe.AuthenticationError as e:
        frappe.throw(_("Invalid username or password"), frappe.AuthenticationError)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Login Error"))
        frappe.throw(_("Login failed. Please try again."))


@frappe.whitelist()
def regenerate_api_keys():
    """
    Allow users to regenerate their own API keys.
    Useful if keys are compromised.
    """
    user = frappe.session.user
    
    if user == "Guest":
        frappe.throw(_("Not authenticated"), frappe.PermissionError)
    
    user_doc = frappe.get_doc("User", user)
    
    # Generate new keys
    api_key = frappe.generate_hash(length=15)
    api_secret = frappe.generate_hash(length=15)
    
    user_doc.api_key = api_key
    user_doc.api_secret = api_secret
    user_doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {
        "success": True,
        "api_key": api_key,
        "api_secret": api_secret,
        "message": "API keys regenerated successfully"
    }