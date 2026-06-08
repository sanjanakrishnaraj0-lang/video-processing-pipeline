"""
generic_agent.py
----------------
AI Agent that analyzes any generic document (identity documents, invoices, receipts, etc.) using Gemini.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from agents.format_manager import get_format_by_id, build_prompt_for_format, DEFAULT_FORMATS
from agents.report_agent import (
    _extract_text_from_pdf,
    _extract_text_from_docx,
    _extract_text_from_excel,
    _extract_text_from_csv
)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

import re

def _extract_local_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    text = ""
    try:
        if ext in (".docx", ".doc"):
            text = _extract_text_from_docx(file_path)
        elif ext == ".pdf":
            text = _extract_text_from_pdf(file_path)
        elif ext in (".xlsx", ".xls"):
            text = _extract_text_from_excel(file_path)
        elif ext == ".csv":
            text = _extract_text_from_csv(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
    except Exception as e:
        print(f"[GenericAgent] Error extracting text locally: {e}")
    return text or ""


def _extract_name_from_filename(filename: str) -> Optional[str]:
    clean_name = os.path.splitext(filename)[0]
    clean_name = re.sub(r'^upload_[a-f0-9\-]+', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '', clean_name, flags=re.IGNORECASE)
    
    name_match = re.search(r'(?:of|card|for|card_of|resume_of)[-\s_]+([a-zA-Z\s_]+)', clean_name, re.IGNORECASE)
    extracted_name = None
    if name_match:
        extracted_name = name_match.group(1).replace("_", " ").strip()
    else:
        words = [w for w in re.split(r'[-\s_]+', clean_name) if w.isalpha() and w.lower() not in [
            "adhar", "aadhaar", "card", "final", "upload", "mb", "good", "copy", "resume", "cv", "report", "summary"
        ]]
        if words:
            extracted_name = " ".join(words)
            
    if extracted_name:
        extracted_name = " ".join([w.capitalize() for w in extracted_name.split()])
        if len(extracted_name) > 2:
            return extracted_name
    return None


def _analyze_text_locally(text: str, file_path: str, fallback_data: dict = None, original_filename: str = None) -> dict:
    filename = original_filename or os.path.basename(file_path)
    lower_text = text.lower()
    
    result = {
        "document_type": "Generic Document",
        "title": filename,
        "summary": "A generic document.",
        "extracted_details": {}
    }
    
    if fallback_data:
        result.update({k: v for k, v in fallback_data.items() if k != "extracted_details"})
        if "extracted_details" in fallback_data:
            result["extracted_details"] = dict(fallback_data["extracted_details"])
            
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return result
        
    is_aadhaar = False
    if any(k in lower_text for k in ["aadhaar", "uidai", "government of india", "unique identification"]):
        result["document_type"] = "Identity Document (Aadhaar Card)"
        is_aadhaar = True
    elif any(k in lower_text for k in ["invoice", "bill to", "invoice number", "amount due"]):
        result["document_type"] = "Invoice"
    elif any(k in lower_text for k in ["receipt", "transaction details", "payment receipt"]):
        result["document_type"] = "Receipt"
    elif any(k in lower_text for k in ["resume", "cv", "curriculum vitae", "work experience"]):
        result["document_type"] = "Resume / CV"
    elif any(k in lower_text for k in ["report", "findings", "summary of findings"]):
        result["document_type"] = "Report"
        
    if len(lines) > 0:
        first_line_clean = re.sub(r'[^\w\s\-\(\)\/\.,]', '', lines[0]).strip()
        if 5 < len(first_line_clean) < 80:
            result["title"] = first_line_clean
            
    details = {}
    aadhaar_pattern = re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
    dob_pattern = re.compile(r'(?:DOB|Date of Birth|Birth|DOB\s*:)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})', re.IGNORECASE)
    email_pattern = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')
    phone_pattern = re.compile(r'\b(?:\+?91)?[-\s]?\d{10}\b')
    gender_pattern = re.compile(r'\b(Male|Female|Transgender|MALE|FEMALE)\b', re.IGNORECASE)

    extracted_name = None
    name_match = re.search(r'(?:name|nam)\s*[:\-]\s*([a-zA-Z\s\.]+)', text, re.IGNORECASE)
    if name_match:
        cand_name = name_match.group(1).split('\n')[0].strip()
        if len(cand_name) > 2 and not any(k in cand_name.lower() for k in ["government", "india", "uidai", "aadhaar", "male", "female", "help", "enrollment", "birth", "dob", "address"]):
            extracted_name = cand_name
            
    if not extracted_name:
        parentage_match = re.search(r'([a-zA-Z\s\.]+)\s+(?:D/O|S/O|W/O|C/O|d/o|s/o|w/o|c/o)', text)
        if parentage_match:
            cand_name = parentage_match.group(1).strip()
            cand_lines = [l.strip() for l in cand_name.splitlines() if l.strip()]
            if cand_lines:
                cand_name = cand_lines[-1]
            cand_name = re.sub(r'^[^\w\s\.]+', '', cand_name).strip()
            if len(cand_name) > 2 and not any(k in cand_name.lower() for k in ["government", "india", "uidai", "aadhaar", "male", "female", "help", "enrollment", "birth", "dob", "address"]):
                extracted_name = cand_name

    if is_aadhaar and not extracted_name:
        for line in lines:
            line_clean = re.sub(r'^[^\w\s\.]+', '', line).strip()
            if (re.match(r'^[a-zA-Z\s\.]+$', line_clean) and len(line_clean) > 2 and 
                not any(k in line_clean.lower() for k in ["government", "india", "uidai", "aadhaar", "male", "female", "help", "enrollment", "birth", "dob", "address", "to"])):
                extracted_name = line_clean
                break

    dob_match = dob_pattern.search(text)
    if dob_match:
        details["Date of Birth"] = dob_match.group(1).strip()
    else:
        generic_dob = re.search(r'\b\d{2}/\d{2}/\d{4}\b', text)
        if generic_dob:
            details["Date of Birth"] = generic_dob.group(0).strip()
        
    gender_match = gender_pattern.search(text)
    if gender_match:
        details["Gender"] = gender_match.group(1).capitalize()
        
    aadhaar_match = aadhaar_pattern.search(text)
    if aadhaar_match:
        details["Aadhaar Number"] = aadhaar_match.group(0).strip()

    emails = email_pattern.findall(text)
    if emails:
        details["Email"] = emails[0].strip()
        
    phones = phone_pattern.findall(text)
    if phones:
        details["Phone Number"] = phones[0].strip()

    if extracted_name:
        extracted_name = " ".join([w.capitalize() for w in extracted_name.split()])
        details["Name"] = extracted_name
        if is_aadhaar:
            result["title"] = f"Aadhaar Card of {extracted_name}"
            result["summary"] = f"Government of India Aadhaar Card national identity document containing {extracted_name}'s details."
        else:
            result["title"] = f"Document of {extracted_name}"
            result["summary"] = f"Document containing details for {extracted_name}."

    extracted_address = None
    address_match = re.search(r'(?:Address)\s*[:\-]?\s*(.*)', text, re.IGNORECASE | re.DOTALL)
    if address_match:
        addr_text = address_match.group(1).strip()
        addr_lines = [l.strip() for l in addr_text.splitlines() if l.strip()]
        clean_addr = []
        for l in addr_lines[:4]:
            if any(k in l.lower() for k in ["signature", "date", "phone", "email", "aadhaar"]):
                break
            clean_addr.append(l)
        if clean_addr:
            extracted_address = ", ".join(clean_addr)
            
    if not extracted_address and is_aadhaar:
        parentage_line_match = re.search(r'(?:D/O|S/O|W/O|C/O|d/o|s/o|w/o|c/o)\s+([^\n]+(?:\n[^\n]+){0,2})', text)
        if parentage_line_match:
            addr_candidate = parentage_line_match.group(0).strip()
            addr_candidate = re.sub(r'\s+', ' ', addr_candidate)
            pin_match = re.search(r'PIN\s*Code\s*:\s*\d{6}|\b\d{6}\b', text, re.IGNORECASE)
            if pin_match and pin_match.group(0) not in addr_candidate:
                addr_candidate += ", PIN Code: " + re.sub(r'[^\d]', '', pin_match.group(0))
            extracted_address = addr_candidate

    if extracted_address:
        details["Address"] = extracted_address

    if not is_aadhaar:
        text_snippet = " ".join(lines[:3])
        if len(text_snippet) > 150:
            text_snippet = text_snippet[:147] + "..."
        result["summary"] = f"This document was detected as a {result['document_type']}. Content snippet: \"{text_snippet}\""

    result["extracted_details"] = details
    return result


def analyze_generic_document(
    file_path: str,
    job_id: str,
    format_id: str = "generic_document",
    system_prompt_template: Optional[str] = None,
    context_prompt: Optional[str] = None,
    fallback: Optional[Dict[str, Any]] = None,
    model_name: str = "gemini-2.0-flash",
    original_filename: Optional[str] = None
) -> dict:
    """
    Main entry point: analyze a generic document and return structured JSON.
    """
    ext = Path(file_path).suffix.lower()
    result_path = os.path.join(os.path.dirname(__file__), "..", f"result_{job_id}.json")

    # Load format
    fmt = get_format_by_id(format_id)
    if not fmt:
        fmt = next((f for f in DEFAULT_FORMATS if f["id"] == "generic_document"), None)

    if context_prompt is None:
        context_str = "Determine the type of this document and extract its key details dynamically."
    else:
        context_str = context_prompt

    prompt = build_prompt_for_format(
        fmt,
        context=context_str,
        system_prompt_template=system_prompt_template
    )

    try:
        data = _analyze_with_gemini(file_path, ext, prompt, model_name)
    except Exception as e:
        print(f"[GenericAgent] Gemini failed ({e}). Attempting local dynamic analysis...")
        local_text = _extract_local_text(file_path)
        if local_text and not local_text.startswith("[Image file"):
            data = _analyze_text_locally(local_text, file_path, fallback, original_filename)
        else:
            filename = original_filename or os.path.basename(file_path)
            data = _fallback_generic_result(fmt, fallback, filename)

    try:
        # Stamp it as generic_document detected agent type
        data["detected_agent_type"] = "other"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[GenericAgent] Result saved to {result_path}")
    except Exception as e:
        print(f"[GenericAgent] Could not save result: {e}")

    return data


def _analyze_with_gemini(file_path: str, ext: str, prompt: str, model_name: str = "gemini-2.0-flash") -> dict:
    """Route file to the right text extractor then send to Gemini."""
    model = genai.GenerativeModel(model_name)

    if ext in (".pdf", ".jpg", ".jpeg", ".png"):
        print("[GenericAgent] Uploading document to Gemini...")
        mime_type = "application/pdf" if ext == ".pdf" else ("image/jpeg" if ext in (".jpg", ".jpeg") else "image/png")
        uploaded = genai.upload_file(file_path, mime_type=mime_type)
        while uploaded.state.name == "PROCESSING":
            time.sleep(2)
            uploaded = genai.get_file(uploaded.name)
        contents = [prompt, uploaded]
    else:
        # Extract text based on file format
        text = ""
        if ext in (".docx", ".doc"):
            text = _extract_text_from_docx(file_path)
        elif ext in (".xlsx", ".xls"):
            text = _extract_text_from_excel(file_path)
        elif ext == ".csv":
            text = _extract_text_from_csv(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        contents = [prompt, f"\n\n--- DOCUMENT CONTENT ---\n{text}"]

    response = model.generate_content(contents)
    result_text = response.text.strip()

    if result_text.startswith("```json"):
        result_text = result_text[7:]
    if result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]

    return json.loads(result_text.strip())


def _fallback_generic_result(fmt: dict, fallback: dict = None, filename: str = None) -> dict:
    filename_lower = filename.lower() if filename else ""
    is_aadhaar_file = any(k in filename_lower for k in ["adhar", "aadhaar", "uidai"])
    
    if is_aadhaar_file:
        name_from_file = _extract_name_from_filename(filename) if filename else None
        details = {
            "File Name": filename if filename else "Aadhaar Card Image",
            "Status": "Analyzed locally",
            "Message": "Visual analysis is not available for image files when Gemini is offline."
        }
        if name_from_file and name_from_file.lower() not in ["image", "upload", "document", "file", "pic", "photo"]:
            details["Name"] = name_from_file
            
        return {
            "document_type": "Identity Document (Aadhaar Card)",
            "title": "Aadhaar Card" + (f" of {name_from_file}" if name_from_file else ""),
            "summary": "Government of India Aadhaar Card national identity document" + (f" containing {name_from_file}'s details" if name_from_file else "") + ".",
            "extracted_details": details
        }
        
    title_name = filename if filename else "Generic Document"
    return {
        "document_type": "Generic Document",
        "title": f"Document: {title_name}",
        "summary": f"A generic document upload named {title_name}.",
        "extracted_details": {
            "File Name": title_name,
            "Status": "Analyzed locally",
            "Message": "This document was analyzed as a generic file. Local OCR is not available for image files when Gemini is offline."
        }
    }
