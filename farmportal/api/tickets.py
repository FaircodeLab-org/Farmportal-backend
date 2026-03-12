import frappe
from frappe.utils import now

@frappe.whitelist(allow_guest=True)
def create_ticket(company_code, tenant_site, subject, description, priority="Medium", module=None, user_email=None):

    ticket = frappe.get_doc({
        "doctype": "Support Ticket",
        "company_code": company_code,
        "tenant_site": tenant_site,
        "user_email": user_email or frappe.session.user,
        "subject": subject,
        "description": description,
        "priority": priority,
        "module": module,
        "status": "Open",
        "created_by": user_email or frappe.session.user or "Guest"
    })

    ticket.insert(ignore_permissions=True)

    return {
        "ticket_id": ticket.name,
        "message": "Ticket created successfully"
    }
    

@frappe.whitelist(allow_guest=True)
def get_tickets(company_code=None):
    filters = {}
    if company_code:
        filters["company_code"] = company_code

    tickets = frappe.get_all(
        "Support Ticket",
        filters=filters,
        fields=[
            "name",
            "company_code",
            "subject",
            "description",
            "status",
            "priority",
            "module",
            "user_email",
            "created_by",
            "tenant_site",
            "creation",
        ],
        ignore_permissions=True
    )

    return tickets


@frappe.whitelist(allow_guest=True)
def add_reply(ticket_id, message, attachment=None, reply_by=None):
    if not ticket_id:
        frappe.throw("ticket_id is required")
    if not message:
        frappe.throw("message is required")

    doc = frappe.get_doc("Support Ticket", ticket_id)
    doc.append("reply", {
        "user": reply_by or frappe.session.user or "Guest",
        "message": message,
        "attachment": attachment,
        "date": now()
    })
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Reply added"}


@frappe.whitelist(allow_guest=True)
def update_status(ticket_id, status, updated_by=None):
    if not ticket_id:
        frappe.throw("ticket_id is required")
    if not status:
        frappe.throw("status is required")

    allowed = {"Open", "In Progress", "Resolved", "Closed"}
    if status not in allowed:
        frappe.throw(f"Invalid status: {status}")

    doc = frappe.get_doc("Support Ticket", ticket_id)
    doc.status = status
    if hasattr(doc, "modified_by"):
        doc.modified_by = updated_by or frappe.session.user or "Guest"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": "Status updated"}


@frappe.whitelist(allow_guest=True)
def get_ticket_detail(ticket_id):
    if not ticket_id:
        frappe.throw("ticket_id is required")

    doc = frappe.get_doc("Support Ticket", ticket_id)
    return {
        "name": doc.name,
        "company_code": doc.company_code,
        "subject": doc.subject,
        "description": doc.description,
        "status": doc.status,
        "priority": doc.priority,
        "created_by": doc.created_by,
        "user_email": doc.user_email,
        "tenant_site": doc.tenant_site,
        "creation": doc.creation,
        "reply": [
            {
                "user": r.user,
                "message": r.message,
                "attachment": r.attachment,
                "date": r.date
            }
            for r in (doc.get("reply") or [])
        ],
    }
