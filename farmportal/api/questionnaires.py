# from __future__ import annotations
# import json
# import frappe
# from frappe import _ as _t

# DT = "Questionnaire"
# CHILD_DT = "Questionnaire Question"

# # reuse your helper from requests.py if available
# try:
#     from farmportal.api.requests import _get_party_from_user  # (customer, supplier)
# except Exception:
#     def _get_party_from_user(user: str):
#         return None, None

# def _as_list(v):
#     if not v:
#         return []
#     if isinstance(v, list):
#         return v
#     try:
#         return json.loads(v)
#     except Exception:
#         return []

# def _ensure_radio_opts(opts):
#     # accept ['A','B'] or "A\nB" and return newline string
#     if isinstance(opts, str):
#         return opts.strip()
#     if isinstance(opts, list):
#         return "\n".join([str(x).strip() for x in opts if str(x).strip()])
#     return ""

# @frappe.whitelist()
# def create_questionnaire(supplier_id: str, title: str, questions: list | str, due_date: str | None = None):
#     """
#     Customer creates a questionnaire with actual questions:
#     questions: list of { question, input_type: 'Radio'|'Text', options?: ['Yes','No'], required?: 0|1 }
#     """
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     customer, supplier_flag = _get_party_from_user(user)
#     if not customer:
#         frappe.throw(_("No Customer linked to your user"), frappe.PermissionError)
#     if supplier_flag and not customer:
#         frappe.throw(_("Suppliers cannot create questionnaires"), frappe.PermissionError)

#     qlist = _as_list(questions)
#     if not qlist:
#         frappe.throw(_("Questions are required"))

#     doc = frappe.new_doc(DT)
#     doc.title = title
#     doc.customer = customer
#     doc.supplier = supplier_id
#     doc.status = "Pending"
#     doc.created_by = user
#     if due_date:
#         doc.due_date = due_date

#     for q in qlist:
#         item = doc.append("questions", {})
#         item.question = q.get("question") or q.get("question_text") or ""
#         item.input_type = (q.get("input_type") or q.get("type") or "Text").title()  # 'Radio' or 'Text'
#         item.required = 1 if q.get("required") else 0
#         if item.input_type == "Radio":
#             item.options_raw = _ensure_radio_opts(q.get("options"))

#     doc.insert(ignore_permissions=True)
#     frappe.db.commit()
#     return {"id": doc.name, "status": doc.status}

# @frappe.whitelist()
# def list_for_me(status: str | None = None):
#     """List questionnaires for the logged-in user (customer-owned or supplier-incoming)."""
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_("Not logged in"), frappe.PermissionError)

#     customer, supplier = _get_party_from_user(user)
#     filters = {}
#     role = None
#     if supplier and not customer:
#         role = "supplier"
#         filters["supplier"] = supplier
#     elif customer:
#         role = "customer"
#         filters["customer"] = customer
#     else:
#         return {"items": [], "role": None}

#     if status:
#         filters["status"] = status

#     rows = frappe.get_all(
#         DT,
#         filters=filters,
#         fields=[
#             "name as id", "title", "customer", "supplier", "status",
#             "due_date", "creation", "modified"
#         ],
#         order_by="creation desc",
#         limit_page_length=200
#     )
#     return {"items": rows, "role": role}

# @frappe.whitelist()
# def get_one(q_id: str):
#     """Return questionnaire with its actual questions."""
#     doc = frappe.get_doc(DT, q_id)
#     # serialize questions (include child row name so we can map answers)
#     questions = []
#     for row in doc.get("questions") or []:
#         opts = (row.options_raw or "").splitlines() if row.input_type == "Radio" else []
#         questions.append({
#             "rowname": row.name,          # child row id for mapping answers
#             "question": row.question,
#             "input_type": row.input_type, # 'Radio' or 'Text'
#             "options": opts,
#             "required": int(row.required or 0),
#             "answer": row.answer or ""
#         })
#     return {
#         "id": doc.name,
#         "title": doc.title,
#         "customer": doc.customer,
#         "supplier": doc.supplier,
#         "status": doc.status,
#         "due_date": doc.due_date,
#         "questions": questions
#     }

# @frappe.whitelist()
# def submit_answers(q_id: str, answers: dict | str = None, message: str | None = None, action: str | None = None):
#     user = frappe.session.user
#     if user == "Guest":
#         frappe.throw(_t("Not logged in"), frappe.PermissionError)

#     _, supplier = _get_party_from_user(user)
#     doc = frappe.get_doc("Questionnaire", q_id)
#     if not supplier or supplier != doc.supplier:
#         frappe.throw(_t("Not permitted to respond"), frappe.PermissionError)

#     # answers may arrive as JSON string, dict, "", or null
#     amap = {}
#     if isinstance(answers, dict):
#         amap = answers
#     elif isinstance(answers, str) and answers.strip():
#         try:
#             amap = json.loads(answers)
#         except Exception:
#             amap = {}

#     child_map = {row.name: row for row in (doc.get("questions") or [])}
#     for rowname, val in amap.items():
#         row = child_map.get(rowname)
#         if row:
#             row.answer = "" if val is None else str(val)

#     if message is not None:
#         doc.response_message = message

#     token = (action or "").strip().lower()
#     if token in {"complete", "accept", "submit", "done"}:
#         doc.status = "Completed"
#         doc.submitted_on = frappe.utils.now_datetime()
#         doc.responded_by = user
#     elif token in {"deny", "reject", "rejected", "decline"}:
#         doc.status = "Denied"
#         doc.responded_by = user

#     doc.save(ignore_permissions=True)
#     frappe.db.commit()
#     return {"id": doc.name, "status": doc.status, "message": _t("Saved")}

from __future__ import annotations
import json
import frappe
from frappe import _ as _t
from frappe.utils.file_manager import save_file

DT = "Questionnaire"
CHILD_DT = "Questionnaire Question"


# Reuse your helper from requests.py if available
try:
    from farmportal.api.requests import _get_party_from_user  # (customer, supplier)
except Exception:
    def _get_party_from_user(user: str):
        return None, None


def _as_list(v):
    """Convert input to list."""
    if not v:
        return []
    if isinstance(v, list):
        return v
    try:
        return json.loads(v)
    except Exception:
        return []


def _ensure_options(opts):
    """Accept ['A','B'] or "A\nB" and return newline string."""
    if isinstance(opts, str):
        return opts.strip()
    if isinstance(opts, list):
        return "\n".join([str(x).strip() for x in opts if str(x).strip()])
    return ""


def _normalize_input_type(input_type: str) -> str:
    """Normalize input type to standard values."""
    type_map = {
        'multiple choice': 'Multiple Choice',
        'radio': 'Multiple Choice',
        'select': 'Multiple Choice',
        'text': 'Text',
        'file upload': 'File',
        'file': 'File',
        'attach': 'File'
    }
    return type_map.get(input_type.lower(), 'Text')


@frappe.whitelist()
def create_questionnaire(supplier_id: str, title: str, questions: list | str, due_date: str | None = None):
    """
    Customer creates a questionnaire with actual questions.
    
    Args:
        supplier_id: ID of the supplier to send questionnaire to
        title: Title of the questionnaire
        questions: List of question objects with structure:
            {
                question: str,
                input_type: 'Text' | 'Multiple Choice' | 'File' | 'File Upload',
                options: list (required for Multiple Choice),
                required: 0 | 1
            }
        due_date: Optional due date in YYYY-MM-DD format
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_t("Not logged in"), frappe.PermissionError)

    customer, supplier_flag = _get_party_from_user(user)
    if not customer:
        frappe.throw(_t("No Customer linked to your user"), frappe.PermissionError)
    if supplier_flag and not customer:
        frappe.throw(_t("Suppliers cannot create questionnaires"), frappe.PermissionError)

    qlist = _as_list(questions)
    if not qlist:
        frappe.throw(_t("Questions are required"))

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
        
        # Normalize input type
        raw_type = q.get("input_type") or q.get("type") or "Text"
        item.input_type = _normalize_input_type(raw_type)
        
        item.required = 1 if q.get("required") else 0
        
        # Handle options for Multiple Choice
        if item.input_type == "Multiple Choice":
            item.options_raw = _ensure_options(q.get("options"))

    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"id": doc.name, "status": doc.status, "message": _t("Questionnaire created successfully")}


@frappe.whitelist()
def list_for_me(status: str | None = None):
    """
    List questionnaires for the logged-in user.
    
    Returns questionnaires where the user is either:
    - The customer (created by them)
    - The supplier (sent to them)
    
    Args:
        status: Optional status filter ('Pending', 'Completed', 'Denied')
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_t("Not logged in"), frappe.PermissionError)

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
            "due_date", "creation", "modified", "responded_by", "submitted_on"
        ],
        order_by="creation desc",
        limit_page_length=200
    )
    return {"items": rows, "role": role}


@frappe.whitelist()
def get_one(q_id: str):
    """
    Return questionnaire with its questions and answers.
    
    Args:
        q_id: Questionnaire ID
        
    Returns:
        Dictionary with questionnaire details and questions array
    """
    doc = frappe.get_doc(DT, q_id)
    
    # Serialize questions (include child row name so we can map answers)
    questions = []
    for row in doc.get("questions") or []:
        opts = []
        if row.input_type == "Multiple Choice":
            opts = (row.options_raw or "").splitlines()
        
        questions.append({
            "rowname": row.name,          # child row id for mapping answers
            "question": row.question,
            "input_type": row.input_type, # 'Multiple Choice', 'Text', or 'File'
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
        "creation": doc.creation,
        "response_message": doc.get("response_message") or "",
        "questions": questions
    }


@frappe.whitelist()
def upload_questionnaire_file(q_id: str, rowname: str):
    """
    Upload a file for a specific questionnaire question.
    Call this before submitting answers to get the file_url.
    
    Args:
        q_id: Questionnaire ID
        rowname: Child table row name (question identifier)
        
    Returns:
        Dictionary with file_url, file_name, and rowname
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_t("Not logged in"), frappe.PermissionError)

    # Verify access
    doc = frappe.get_doc(DT, q_id)
    _, supplier = _get_party_from_user(user)
    
    if not supplier or supplier != doc.supplier:
        frappe.throw(_t("Not permitted to upload files"), frappe.PermissionError)

    # Verify questionnaire is in editable state
    if doc.status not in ["Pending", "Draft"]:
        frappe.throw(_t("Cannot upload files to completed questionnaire"))

    # Get the uploaded file from request
    if 'file' not in frappe.request.files:
        frappe.throw(_t("No file uploaded"))

    uploaded_file = frappe.request.files['file']
    
    if not uploaded_file.filename:
        frappe.throw(_t("Invalid file"))
    
    file_name = uploaded_file.filename
    file_data = uploaded_file.read()

    # Verify this is a file-type question
    child_map = {row.name: row for row in (doc.get("questions") or [])}
    question_row = child_map.get(rowname)
    
    if not question_row:
        frappe.throw(_t("Question not found"))
    
    if question_row.input_type != "File":
        frappe.throw(_t("This question does not accept file uploads"))

    # Save file attached to the questionnaire document
    saved_file = save_file(
        fname=file_name,
        content=file_data,
        dt=DT,
        dn=q_id,
        is_private=1
    )

    frappe.db.commit()

    # Return the file URL to store in the answer
    return {
        "file_url": saved_file.file_url,
        "file_name": saved_file.file_name,
        "rowname": rowname,
        "message": _t("File uploaded successfully")
    }


@frappe.whitelist()
def submit_answers(q_id: str, answers: dict | str = None, message: str | None = None, action: str | None = None):
    """
    Submit or update answers for a questionnaire.
    
    Args:
        q_id: Questionnaire ID
        answers: Dictionary mapping rowname to answer value (for File type, should be file_url)
        message: Optional response message
        action: Optional action ('complete', 'deny', etc.)
        
    Returns:
        Dictionary with updated status
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_t("Not logged in"), frappe.PermissionError)

    _, supplier = _get_party_from_user(user)
    doc = frappe.get_doc(DT, q_id)
    
    if not supplier or supplier != doc.supplier:
        frappe.throw(_t("Not permitted to respond"), frappe.PermissionError)

    # Parse answers - may arrive as JSON string, dict, "", or null
    amap = {}
    if isinstance(answers, dict):
        amap = answers
    elif isinstance(answers, str) and answers.strip():
        try:
            amap = json.loads(answers)
        except Exception:
            amap = {}

    # Update child table answers
    child_map = {row.name: row for row in (doc.get("questions") or [])}
    for rowname, val in amap.items():
        row = child_map.get(rowname)
        if row:
            # For File type, val should be the file_url after upload
            # For Text/Multiple Choice, it's the actual answer
            row.answer = "" if val is None else str(val)

    if message is not None:
        doc.response_message = message

    # Handle status changes based on action
    token = (action or "").strip().lower()
    if token in {"complete", "accept", "submit", "done"}:
        # Validate required fields before completing
        missing_required = []
        for row in (doc.get("questions") or []):
            if row.required and not row.answer:
                missing_required.append(row.question)
        
        if missing_required:
            frappe.throw(
                _t("Please answer all required questions: {0}").format(", ".join(missing_required))
            )
        
        doc.status = "Completed"
        doc.submitted_on = frappe.utils.now_datetime()
        doc.responded_by = user
    elif token in {"deny", "reject", "rejected", "decline"}:
        doc.status = "Denied"
        doc.responded_by = user
        if not message:
            doc.response_message = "Denied by supplier"

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {
        "id": doc.name,
        "status": doc.status,
        "message": _t("Saved successfully")
    }


@frappe.whitelist()
def delete_questionnaire(q_id: str):
    """
    Delete a questionnaire (customer only).
    
    Args:
        q_id: Questionnaire ID
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_t("Not logged in"), frappe.PermissionError)

    customer, _ = _get_party_from_user(user)
    doc = frappe.get_doc(DT, q_id)
    
    if not customer or customer != doc.customer:
        frappe.throw(_t("Not permitted to delete"), frappe.PermissionError)
    
    doc.delete(ignore_permissions=True)
    frappe.db.commit()
    
    return {"message": _t("Questionnaire deleted successfully")}
