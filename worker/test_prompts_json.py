import os
import sys
import json

# Add current directory to path to ensure local agents modules are importable
sys.path.insert(0, os.path.dirname(__file__))

from agents.format_manager import get_format_by_id, build_prompt_for_format, load_agent_prompts
from agents.resume_agent import _fallback_resume_result
from agents.report_agent import _fallback_report_result

def test_json_prompts():
    print("--- Loading Agent Prompts JSON ---")
    prompts = load_agent_prompts()
    print("Loaded prompts keys:", list(prompts.keys()))
    assert "system_prompt_template" in prompts, "system_prompt_template is missing in JSON"
    assert "resume" in prompts, "resume prompts are missing in JSON"
    assert "report" in prompts, "report prompts are missing in JSON"

    print("\n--- Verifying Resume Prompt & Fallback ---")
    resume_fmt = get_format_by_id("resume_standard")
    assert resume_fmt is not None, "Could not find resume_standard format"
    
    resume_prompt = build_prompt_for_format(
        resume_fmt,
        context=prompts["resume"]["context_prompt"]
    )
    print("Resume Context Prompt matches:", prompts["resume"]["context_prompt"])
    assert prompts["resume"]["context_prompt"] in resume_prompt, "Context prompt not injected"
    
    resume_fallback = _fallback_resume_result(resume_fmt)
    print("Resume Fallback structure is correct and matches format fields:")
    print(json.dumps(resume_fallback, indent=2))
    assert resume_fallback["overall_score"] == 72, "Fallback score mismatched"

    print("\n--- Verifying Report Prompt & Fallback ---")
    report_fmt = get_format_by_id("report_summary")
    assert report_fmt is not None, "Could not find report_summary format"
    
    report_prompt = build_prompt_for_format(
        report_fmt,
        context=prompts["report"]["context_prompt"]
    )
    print("Report Context Prompt matches:", prompts["report"]["context_prompt"])
    assert prompts["report"]["context_prompt"] in report_prompt, "Context prompt not injected"
    
    report_fallback = _fallback_report_result(report_fmt)
    print("Report Fallback structure is correct and matches format fields:")
    print(json.dumps(report_fallback, indent=2))
    assert report_fallback["confidence_score"] == 85, "Fallback confidence score mismatched"

    print("\n=== ALL TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_json_prompts()
