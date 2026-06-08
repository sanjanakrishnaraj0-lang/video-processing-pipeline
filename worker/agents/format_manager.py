"""
format_manager.py
-----------------
Manages user-defined output formats for all AI agents.
A format defines what fields the AI should return in its JSON output.
"""

import os
import json
from typing import List, Dict, Any

FORMATS_FILE = os.path.join(os.path.dirname(__file__), "..", "formats.json")

# ── Default built-in formats ───────────────────────────────────────────────────
DEFAULT_FORMATS = [
    {
        "id": "video_training_default",
        "name": "Video Training Analysis",
        "agent_type": "video",
        "fields": [
            {"key": "skill_score",       "label": "Skill Score (0-100)",   "type": "number", "description": "Overall skill score out of 100"},
            {"key": "missing_steps",     "label": "Missing Steps",          "type": "list",   "description": "Steps skipped or done incorrectly"},
            {"key": "safety_violations", "label": "Safety Violations",      "type": "list",   "description": "PPE or safety rule violations"},
            {"key": "mcqs",              "label": "Quiz Questions (MCQs)",  "type": "mcq",    "description": "2 multiple choice questions"}
        ]
    },
    {
        "id": "resume_standard",
        "name": "Resume Standard Analysis",
        "agent_type": "resume",
        "fields": [
            {"key": "overall_score",      "label": "Overall Score (0-100)",  "type": "number", "description": "Candidate overall score"},
            {"key": "technical_skills",   "label": "Technical Skills",        "type": "list",   "description": "List of technical skills found"},
            {"key": "soft_skills",        "label": "Soft Skills",             "type": "list",   "description": "Communication, leadership etc."},
            {"key": "experience_years",   "label": "Years of Experience",     "type": "number", "description": "Total years of work experience"},
            {"key": "education_level",    "label": "Education Level",         "type": "text",   "description": "Highest qualification"},
            {"key": "strengths",          "label": "Key Strengths",           "type": "list",   "description": "Strong points of the candidate"},
            {"key": "red_flags",          "label": "Red Flags",               "type": "list",   "description": "Concerns or gaps"},
            {"key": "hire_recommendation","label": "Hire Recommendation",     "type": "text",   "description": "Yes / No / Maybe with reason"}
        ]
    },
    {
        "id": "report_summary",
        "name": "Report Summary Analysis",
        "agent_type": "report",
        "fields": [
            {"key": "summary",          "label": "Executive Summary",       "type": "text",   "description": "Short summary of the document"},
            {"key": "key_findings",     "label": "Key Findings",            "type": "list",   "description": "Main findings or data points"},
            {"key": "risks",            "label": "Risks / Issues",          "type": "list",   "description": "Problems or risks identified"},
            {"key": "recommendations",  "label": "Recommendations",         "type": "list",   "description": "Suggested actions"},
            {"key": "sentiment",        "label": "Overall Sentiment",       "type": "text",   "description": "Positive / Neutral / Negative"},
            {"key": "confidence_score", "label": "Confidence Score (0-100)","type": "number", "description": "AI confidence in analysis"}
        ]
    },
    {
        "id": "generic_document",
        "name": "Generic Document Analysis",
        "agent_type": "other",
        "fields": [
            {"key": "document_type",     "label": "Document Type",      "type": "text",   "description": "Category of the document (e.g. Identity Document, Aadhaar Card, Invoice, Receipt, Other)"},
            {"key": "title",             "label": "Document Title",     "type": "text",   "description": "A clear title for the document"},
            {"key": "summary",           "label": "Document Summary",   "type": "text",   "description": "Executive summary of the document contents"},
            {"key": "extracted_details", "label": "Extracted Details",  "type": "object", "description": "Key-value pair dictionary of important extracted details from the document"}
        ]
    }
]


def _load_all() -> List[Dict[str, Any]]:
    """Load all formats from disk, initializing with defaults if needed."""
    if not os.path.exists(FORMATS_FILE):
        _save_all(DEFAULT_FORMATS)
        return DEFAULT_FORMATS
    try:
        with open(FORMATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_FORMATS


def _save_all(formats: List[Dict[str, Any]]) -> None:
    """Persist all formats to disk."""
    os.makedirs(os.path.dirname(FORMATS_FILE), exist_ok=True)
    with open(FORMATS_FILE, "w", encoding="utf-8") as f:
        json.dump(formats, f, indent=2)


def get_all_formats() -> List[Dict[str, Any]]:
    """Return all saved formats."""
    return _load_all()


def get_format_by_id(format_id: str) -> Dict[str, Any] | None:
    """Retrieve a single format by its ID."""
    for fmt in _load_all():
        if fmt.get("id") == format_id:
            return fmt
    return None


def save_format(fmt: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a format. Generates an ID if missing."""
    import uuid
    formats = _load_all()
    if not fmt.get("id"):
        fmt["id"] = str(uuid.uuid4())
    # Replace existing or append
    updated = False
    for i, existing in enumerate(formats):
        if existing.get("id") == fmt["id"]:
            formats[i] = fmt
            updated = True
            break
    if not updated:
        formats.append(fmt)
    _save_all(formats)
    return fmt


def delete_format(format_id: str) -> bool:
    """Delete a format by ID. Returns True if deleted."""
    formats = _load_all()
    new_formats = [f for f in formats if f.get("id") != format_id]
    if len(new_formats) == len(formats):
        return False
    _save_all(new_formats)
    return True


PROMPTS_FILE = os.path.join(os.path.dirname(__file__), "..", "agent_prompts.json")


def load_agent_prompts() -> Dict[str, Any]:
    """Load agent prompts from disk."""
    if os.path.exists(PROMPTS_FILE):
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: could not load agent prompts from {PROMPTS_FILE}: {e}")
    return {}


def build_prompt_for_format(fmt: Dict[str, Any], context: str = "", system_prompt_template: str = None) -> str:
    """
    Build a Gemini prompt that instructs the model to return JSON
    matching the given format schema.
    """
    fields = fmt.get("fields", [])
    field_descriptions = []
    json_example_lines = []

    for field in fields:
        key = field["key"]
        label = field.get("label", key)
        ftype = field.get("type", "text")
        desc = field.get("description", "")

        field_descriptions.append(f'  - "{key}" ({ftype}): {label} — {desc}')

        if ftype == "number":
            json_example_lines.append(f'  "{key}": 0')
        elif ftype == "list":
            json_example_lines.append(f'  "{key}": ["item1", "item2"]')
        elif ftype == "boolean":
            json_example_lines.append(f'  "{key}": true')
        elif ftype == "mcq":
            json_example_lines.append(
                f'  "{key}": [{{"question": "...", "options": ["A","B","C","D"], "answer": "A"}}]'
            )
        elif ftype in ("object", "dict"):
            json_example_lines.append(f'  "{key}": {{"key1": "val1", "key2": "val2"}}')
        else:
            json_example_lines.append(f'  "{key}": "..."')

    fields_text = "\n".join(field_descriptions)
    json_template = "{\n" + ",\n".join(json_example_lines) + "\n}"

    default_template = "You are an expert AI analyst. {context}\n\nAnalyze the provided content carefully and return a response as a STRICT JSON object with exactly these fields:\n\n{fields_text}\n\nYour response MUST follow this exact JSON structure:\n{json_template}\n\nRules:\n- Output ONLY the raw JSON object. No markdown, no explanation, no extra text.\n- All list fields must be arrays of strings.\n- All number fields must be integers or floats.\n- If information is not available, use an empty list [] or 0 or \"N/A\" as appropriate."
    template = system_prompt_template or default_template

    prompt = template.format(
        context=context,
        fields_text=fields_text,
        json_template=json_template
    )
    return prompt


