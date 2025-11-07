import frappe

def add_cors_headers():
    """Add CORS headers to allow requests from Vercel frontend"""
    if frappe.local.response:
        headers = frappe.local.response.get("headers", {})
        headers.update({
            "Access-Control-Allow-Origin": "https://farm-portal-2cpb.vercel.app",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Frappe-CSRF-Token, Accept",
            "Access-Control-Expose-Headers": "X-Frappe-CSRF-Token",
        })
        frappe.local.response["headers"] = headers

def handle_options():
    """Handle OPTIONS preflight requests"""
    if frappe.request.method == "OPTIONS":
        add_cors_headers()
        frappe.local.response = frappe.Response()
        frappe.local.response.status_code = 200
        return frappe.local.response
