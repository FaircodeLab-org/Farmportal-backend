from __future__ import annotations
import json
import frappe
from frappe import _ as _t

DT = "Questionnaire"
CHILD_DT = "Questionnaire Question"

# reuse your helper from requests.py if available
try:
    from farmportal.api.requests import _get_party_from_user  # (customer, supplier)
except Exception:
    def _get_party_from_user(user: str):
        return None, None

def _as_list(v):
    if not v:
        return []
    if isinstance(v, list):
        return v
    try:
        return json.loads(v)
    except Exception:
        return []

def _ensure_radio_opts(opts):
    # accept ['A','B'] or "A\nB" and return newline string
    if isinstance(opts, str):
        return opts.strip()
    if isinstance(opts, list):
        return "\n".join([str(x).strip() for x in opts if str(x).strip()])
    return ""

@frappe.whitelist()
def create_questionnaire(supplier_id: str, title: str, questions: list | str, due_date: str | None = None):
    """
    Customer creates a questionnaire with actual questions:
    questions: list of { question, input_type: 'Radio'|'Text', options?: ['Yes','No'], required?: 0|1 }
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier_flag = _get_party_from_user(user)
    if not customer:
        frappe.throw(_("No Customer linked to your user"), frappe.PermissionError)
    if supplier_flag and not customer:
        frappe.throw(_("Suppliers cannot create questionnaires"), frappe.PermissionError)

    qlist = _as_list(questions)
    if not qlist:
        frappe.throw(_("Questions are required"))

    doc = frappe.new_doc(DT)
    doc.title = title
    doc.customer = customer
    doc.supplier = supplier_id
    doc.status = "Pending"
    doc.created_by = user
    if due_date:
        doc.due_date = due_date

    for q in qlist:
        item = doc.append("questions", {})
        item.question = q.get("question") or q.get("question_text") or ""
        item.input_type = (q.get("input_type") or q.get("type") or "Text").title()  # 'Radio' or 'Text'
        item.required = 1 if q.get("required") else 0
        if item.input_type == "Radio":
            item.options_raw = _ensure_radio_opts(q.get("options"))

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"id": doc.name, "status": doc.status}

@frappe.whitelist()
def list_for_me(status: str | None = None):
    """List questionnaires for the logged-in user (customer-owned or supplier-incoming)."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("Not logged in"), frappe.PermissionError)

    customer, supplier = _get_party_from_user(user)
    filters = {}
    role = None
    if supplier and not customer:
        role = "supplier"
        filters["supplier"] = supplier
    elif customer:
        role = "customer"
        filters["customer"] = customer
    else:
        return {"items": [], "role": None}

    if status:
        filters["status"] = status

    rows = frappe.get_all(
        DT,
        filters=filters,
        fields=[
            "name as id", "title", "customer", "supplier", "status",
            "due_date", "creation", "modified"
        ],
        order_by="creation desc",
        limit_page_length=200
    )
    return {"items": rows, "role": role}

@frappe.whitelist()
def get_one(q_id: str):
    """Return questionnaire with its actual questions."""
    doc = frappe.get_doc(DT, q_id)
    # serialize questions (include child row name so we can map answers)
    questions = []
    for row in doc.get("questions") or []:
        opts = (row.options_raw or "").splitlines() if row.input_type == "Radio" else []
        questions.append({
            "rowname": row.name,          # child row id for mapping answers
            "question": row.question,
            "input_type": row.input_type, # 'Radio' or 'Text'
            "options": opts,
            "required": int(row.required or 0),
            "answer": row.answer or ""
        })
    return {
        "id": doc.name,
        "title": doc.title,
        "customer": doc.customer,
        "supplier": doc.supplier,
        "status": doc.status,
        "due_date": doc.due_date,
        "questions": questions
    }

@frappe.whitelist()
def submit_answers(q_id: str, answers: dict | str = None, message: str | None = None, action: str | None = None):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_t("Not logged in"), frappe.PermissionError)

    _, supplier = _get_party_from_user(user)
    doc = frappe.get_doc("Questionnaire", q_id)
    if not supplier or supplier != doc.supplier:
        frappe.throw(_t("Not permitted to respond"), frappe.PermissionError)

    # answers may arrive as JSON string, dict, "", or null
    amap = {}
    if isinstance(answers, dict):
        amap = answers
    elif isinstance(answers, str) and answers.strip():
        try:
            amap = json.loads(answers)
        except Exception:
            amap = {}

    child_map = {row.name: row for row in (doc.get("questions") or [])}
    for rowname, val in amap.items():
        row = child_map.get(rowname)
        if row:
            row.answer = "" if val is None else str(val)

    if message is not None:
        doc.response_message = message

    token = (action or "").strip().lower()
    if token in {"complete", "accept", "submit", "done"}:
        doc.status = "Completed"
        doc.submitted_on = frappe.utils.now_datetime()
        doc.responded_by = user
    elif token in {"deny", "reject", "rejected", "decline"}:
        doc.status = "Denied"
        doc.responded_by = user

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"id": doc.name, "status": doc.status, "message": _t("Saved")}
