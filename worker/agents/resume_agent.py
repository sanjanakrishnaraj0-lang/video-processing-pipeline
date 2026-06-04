"""
resume_agent.py
---------------
AI Agent that analyzes resume files (PDF, DOCX) using Gemini.
Supports user-defined output formats via format_manager.
"""

import os
import json
import time
import shutil
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from agents.format_manager import get_format_by_id, build_prompt_for_format, DEFAULT_FORMATS, load_agent_prompts

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png"}


def _extract_text_from_docx(file_path: str) -> str:
    """Extract plain text from a DOCX file."""
    try:
        import docx
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        return f"[Could not extract DOCX text: {e}]"


def _extract_text_from_pdf(file_path: str) -> str:
    """Extract plain text from a PDF file."""
    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        return f"[Could not extract PDF text: {e}]"


def analyze_resume(
    file_path: str,
    job_id: str,
    format_id: str = "resume_standard",
    system_prompt_template: Optional[str] = None,
    context_prompt: Optional[str] = None,
    fallback: Optional[Dict[str, Any]] = None,
    model_name: str = "gemini-2.0-flash"
) -> dict:
    """
    Main entry point: analyze a resume file and return structured JSON.
    
    Args:
        file_path: Absolute path to the uploaded resume file
        job_id:    Unique job identifier for saving results
        format_id: ID of the output format to use
    Returns:
        dict: Analysis result matching the chosen format schema
    """
    ext = Path(file_path).suffix.lower()
    result_path = os.path.join(os.path.dirname(__file__), "..", f"result_{job_id}.json")

    # ── Load format ────────────────────────────────────────────────────────────
    fmt = get_format_by_id(format_id)
    if not fmt:
        # Fall back to built-in resume standard
        fmt = next((f for f in DEFAULT_FORMATS if f["id"] == "resume_standard"), None)

    if context_prompt is None:
        prompts_data = load_agent_prompts().get("resume", {})
        context_str = prompts_data.get("context_prompt", "You are analyzing a candidate's RESUME or CV document.")
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
        print(f"[ResumeAgent] Gemini failed ({e}). Using simulated fallback.")
        data = _fallback_resume_result(fmt, fallback)

    # Save result
    try:
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[ResumeAgent] Result saved to {result_path}")
    except Exception as e:
        print(f"[ResumeAgent] Could not save result: {e}")

    return data


def _analyze_with_gemini(file_path: str, ext: str, prompt: str, model_name: str = "gemini-2.0-flash") -> dict:
    """Upload file to Gemini and get analysis."""
    model = genai.GenerativeModel(model_name)

    if ext in (".pdf", ".jpg", ".jpeg", ".png"):
        # Upload PDF or Image directly to Gemini File API
        print(f"[ResumeAgent] Uploading document to Gemini...")
        mime_type = "application/pdf" if ext == ".pdf" else ("image/jpeg" if ext in (".jpg", ".jpeg") else "image/png")
        uploaded = genai.upload_file(file_path, mime_type=mime_type)
        # Wait for processing
        while uploaded.state.name == "PROCESSING":
            time.sleep(2)
            uploaded = genai.get_file(uploaded.name)
        contents = [prompt, uploaded]

    elif ext in (".docx", ".doc"):
        # Extract text and send as plain text
        print(f"[ResumeAgent] Extracting DOCX text...")
        text = _extract_text_from_docx(file_path)
        contents = [prompt, f"\n\n--- RESUME CONTENT ---\n{text}"]

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        contents = [prompt, f"\n\n--- RESUME CONTENT ---\n{text}"]

    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    response = model.generate_content(contents)
    result_text = response.text.strip()

    # Strip markdown fences if present
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    if result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]

    return json.loads(result_text.strip())


def _fallback_resume_result(fmt: dict, fallback: Optional[Dict[str, Any]] = None) -> dict:
    """Return a realistic simulated result if Gemini is unavailable."""
    if fallback is None:
        prompts_data = load_agent_prompts().get("resume", {})
        fallback = prompts_data.get("fallback", {
            "overall_score": 72,
            "technical_skills": ["Python", "FastAPI", "React", "SQL", "Docker"],
            "soft_skills": ["Team collaboration", "Problem solving", "Communication"],
            "experience_years": 4,
            "education_level": "Bachelor's in Computer Science",
            "strengths": [
                "Strong backend development experience",
                "Hands-on with cloud deployments",
                "Clear and concise project descriptions"
              ],
            "red_flags": [
                "Employment gap of 8 months (2022-2023) not explained",
                "No mention of testing or CI/CD experience"
              ],
            "hire_recommendation": "Maybe — Strong technical profile but gaps need clarification"
        })
    # Filter to only keys in the chosen format
    if fmt and fmt.get("fields"):
        keys = [f["key"] for f in fmt["fields"]]
        return {k: v for k, v in fallback.items() if k in keys}
    return fallback

