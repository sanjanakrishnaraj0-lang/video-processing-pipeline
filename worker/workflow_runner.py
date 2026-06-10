import os
import json
from typing import Dict, Any, List

# Import helper functions
from process_video import download_video, extract_audio, extract_frames, analyze_with_ai
from agents.resume_agent import analyze_resume
from agents.report_agent import analyze_report
from agents.generic_agent import analyze_generic_document

class WorkflowRunner:
    def __init__(self, workflows_file: str = None):
        if workflows_file is None:
            workflows_file = os.path.join(os.path.dirname(__file__), "workflows.json")
        with open(workflows_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.workflows = {w["workflow_id"]: w for w in self.config.get("workflows", [])}

    def run_workflow(self, workflow_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            # Fallback for compatibility (e.g. video_processing_pipeline -> video)
            if "video" in workflow_id:
                workflow = self.workflows.get("video")
            elif "resume" in workflow_id:
                workflow = self.workflows.get("resume")
            elif "report" in workflow_id:
                workflow = self.workflows.get("report")

        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found in configuration.")

        # Keep track of outputs from each step
        step_outputs: Dict[str, Any] = {}

        print(f"\n[WorkflowRunner] Starting workflow: {workflow_id} ({workflow.get('description', '')})")

        for step in workflow.get("steps", []):
            step_id = step["step_id"]
            action = step["action"]
            depends_on = step.get("depends_on", [])
            params = step.get("parameters", {})

            print(f"[WorkflowRunner] Running step '{step_id}' - action '{action}'")

            # Execute step based on action type
            try:
                output = self._execute_action(action, step_id, params, job_data, step_outputs)
                step_outputs[step_id] = output
                print(f"[WorkflowRunner] Step '{step_id}' completed successfully.")
            except Exception as e:
                print(f"[WorkflowRunner] Error in step '{step_id}': {e}")
                raise e

        # Return the final step output
        final_step = workflow.get("steps", [])[-1]["step_id"]
        return step_outputs.get(final_step, {})

    def _execute_action(
        self,
        action: str,
        step_id: str,
        params: Dict[str, Any],
        job_data: Dict[str, Any],
        step_outputs: Dict[str, Any]
    ) -> Any:
        job_id = job_data.get("job_id") or job_data.get("video_id")
        format_id = job_data.get("format_id")
        golden_standard = job_data.get("golden_standard")

        if action == "ai.classify_file":
            file_path = job_data.get("file_path") or job_data.get("video_path")
            if not file_path:
                raise ValueError("No file_path provided for file classification.")
            
            ext = os.path.splitext(file_path)[1].lower()
            if ext in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
                return {"classification": "video"}
            
            if ext in (".jpg", ".jpeg", ".png"):
                try:
                    import google.generativeai as genai
                    import PIL.Image
                    img = PIL.Image.open(file_path)
                    
                    system_prompt = params.get("system_prompt", "You are an expert document classifier.")
                    prompt_template = params.get("prompt_template", "Classify the following text snippet:\n\n{text_snippet}\n\nRespond with a raw JSON object containing a single field 'classification' which must be one of: 'resume', 'report', or 'other'. Example: {\"classification\": \"resume\"}")
                    prompt = prompt_template.replace("{text_snippet}", "Analyze this uploaded document image.")
                    
                    model_name = params.get("model", "gemini-2.5-flash")
                    model = genai.GenerativeModel(
                        model_name,
                        system_instruction=system_prompt
                    )
                    response = model.generate_content([prompt, img])
                    result_text = response.text.strip()
                    
                    if result_text.startswith("```json"):
                        result_text = result_text[7:]
                    if result_text.startswith("```"):
                        result_text = result_text[3:]
                    if result_text.endswith("```"):
                        result_text = result_text[:-3]
                    
                    data = json.loads(result_text.strip())
                    classification = data.get("classification", "other").lower().strip()
                except Exception as e:
                    print(f"[WorkflowRunner] Gemini image classification failed ({e}). Defaulting to other/filename check.")
                    classification = "other"
                    filename = (job_data.get("original_filename") or "").lower()
                    if any(k in filename for k in ["resume", "cv"]):
                        classification = "resume"
                    elif any(k in filename for k in ["report", "summary", "finding"]):
                        classification = "report"
                
                if classification not in ("resume", "report", "video"):
                    classification = "other"
                print(f"[WorkflowRunner] Image classified as: {classification}")
                return {"classification": classification}

            # Extract text snippet for document classification
            text = ""
            try:
                if ext in (".docx", ".doc"):
                    from agents.resume_agent import _extract_text_from_docx
                    text = _extract_text_from_docx(file_path)
                elif ext == ".pdf":
                    from agents.resume_agent import _extract_text_from_pdf
                    text = _extract_text_from_pdf(file_path)
                elif ext in (".xlsx", ".xls"):
                    from agents.report_agent import _extract_text_from_excel
                    text = _extract_text_from_excel(file_path)
                elif ext == ".csv":
                    from agents.report_agent import _extract_text_from_csv
                    text = _extract_text_from_csv(file_path)
                elif ext == ".txt":
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
            except Exception as e:
                print(f"[WorkflowRunner] Classification text extraction failed: {e}")
            
            text_snippet = (text or "").strip()[:1000]
            classification = "other"
            
            if text_snippet:
                system_prompt = params.get("system_prompt", "You are an expert document classifier.")
                prompt_template = params.get("prompt_template", "Classify the following text: {text_snippet}")
                prompt = prompt_template.replace("{text_snippet}", text_snippet)
                
                try:
                    import google.generativeai as genai
                    model_name = params.get("model", "gemini-1.5-flash-latest")
                    model = genai.GenerativeModel(
                        model_name,
                        system_instruction=system_prompt
                    )
                    response = model.generate_content([prompt])
                    result_text = response.text.strip()
                    
                    if result_text.startswith("```json"):
                        result_text = result_text[7:]
                    if result_text.startswith("```"):
                        result_text = result_text[3:]
                    if result_text.endswith("```"):
                        result_text = result_text[:-3]
                    
                    data = json.loads(result_text.strip())
                    classification = data.get("classification", "other").lower().strip()
                except Exception as e:
                    print(f"[WorkflowRunner] Gemini classification failed ({e}). Using keyword checks.")
                    lower_text = text_snippet.lower()
                    if any(k in lower_text for k in ["skills", "experience", "resume", "cv", "education", "employment"]):
                        classification = "resume"
                    elif any(k in lower_text for k in ["summary", "report", "financial", "revenue", "q3", "q4", "risks", "findings"]):
                        classification = "report"
            
            if classification not in ("resume", "report", "video"):
                classification = "other"
            
            # Filename-based fallback if classification is still other
            if classification == "other":
                filename = (job_data.get("original_filename") or "").lower()
                if any(k in filename for k in ["resume", "cv"]):
                    classification = "resume"
                elif any(k in filename for k in ["report", "summary", "finding"]):
                    classification = "report"
            
            print(f"[WorkflowRunner] File classified as: {classification}")
            return {"classification": classification}

        elif action == "storage.download_file":
            video_url = job_data.get("video_url")
            video_path = job_data.get("video_path") or job_data.get("file_path")

            if video_url:
                local_path = f"downloads/video_{job_id}.mp4"
                os.makedirs("downloads", exist_ok=True)
                download_video(video_url, local_path)
                return {"local_path": local_path}
            elif video_path:
                return {"local_path": video_path}
            else:
                raise ValueError("No media source (video_url or local video_path) provided for download.")

        elif action == "video.extract_audio":
            download_step = step_outputs.get("download_media", {})
            video_path = download_step.get("local_path")
            if not video_path:
                raise ValueError("Dependency 'download_media' did not output a local_path.")

            audio_path = f"downloads/audio_{job_id}.mp3"
            os.makedirs("downloads", exist_ok=True)
            extract_audio(video_path, audio_path)
            return {"audio_path": audio_path}

        elif action == "video.extract_frames":
            download_step = step_outputs.get("download_media", {})
            video_path = download_step.get("local_path")
            if not video_path:
                raise ValueError("Dependency 'download_media' did not output a local_path.")

            frames_dir = f"frames/{job_id}"
            os.makedirs(frames_dir, exist_ok=True)
            extract_frames(video_path, frames_dir)
            return {"frames_dir": frames_dir}

        elif action == "ai.analyze_video":
            download_step = step_outputs.get("download_media", {})
            video_path = download_step.get("local_path")
            
            audio_step = step_outputs.get("extract_audio", {})
            audio_path = audio_step.get("audio_path")
            
            frames_step = step_outputs.get("extract_frames", {})
            frames_dir = frames_step.get("frames_dir")

            if not video_path or not audio_path or not frames_dir:
                raise ValueError("Missing video_path, audio_path, or frames_dir outputs from dependency steps.")

            result_path = f"result_{job_id}.json"
            
            # Resolve custom prompts and fallbacks from workflows.json parameters
            system_prompt_template = params.get("system_prompt_template")
            model_name = params.get("model", "gemini-2.5-flash")
            golden_standards = params.get("golden_standards", {})
            standard_info = golden_standards.get(golden_standard or "general", golden_standards.get("general", {}))
            
            context_prompt = standard_info.get("context_prompt")
            fallback = standard_info.get("fallback")

            return analyze_with_ai(
                audio_path=audio_path,
                frames_dir=frames_dir,
                result_path=result_path,
                format_id=format_id or "video_training_default",
                golden_standard=golden_standard,
                system_prompt_template=system_prompt_template,
                context_prompt=context_prompt,
                fallback=fallback,
                model_name=model_name
            )

        elif action == "document.extract_text":
            file_path = job_data.get("file_path") or job_data.get("video_path")
            if not file_path:
                raise ValueError("No file_path provided for document text extraction.")
            
            ext = os.path.splitext(file_path)[1].lower()
            text = ""
            if ext in (".docx", ".doc"):
                from agents.resume_agent import _extract_text_from_docx
                text = _extract_text_from_docx(file_path)
            elif ext == ".pdf":
                from agents.resume_agent import _extract_text_from_pdf
                text = _extract_text_from_pdf(file_path)
            elif ext in (".xlsx", ".xls"):
                from agents.report_agent import _extract_text_from_excel
                text = _extract_text_from_excel(file_path)
            elif ext == ".csv":
                from agents.report_agent import _extract_text_from_csv
                text = _extract_text_from_csv(file_path)
            elif ext == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            elif ext in (".jpg", ".jpeg", ".png"):
                text = "[Image file — content will be analyzed directly from the image by Gemini]"
            else:
                raise ValueError(f"Unsupported document extension: {ext}")
            
            return {"extracted_text": text, "file_path": file_path}

        elif action == "ai.analyze_document":
            ocr_step = step_outputs.get("ocr_extraction", {})
            text = ocr_step.get("extracted_text")
            file_path = ocr_step.get("file_path")
            
            if text is None or not file_path:
                raise ValueError("Dependency 'ocr_extraction' did not output extracted_text or file_path.")

            agent_type = params.get("agent_type", "resume")
            system_prompt_template = params.get("system_prompt_template")
            model_name = params.get("model", "gemini-2.5-flash")

            golden_standards = params.get("golden_standards", {})
            if golden_standards:
                standard_info = golden_standards.get(golden_standard or "general", golden_standards.get("general", {}))
                context_prompt = standard_info.get("context_prompt", params.get("context_prompt"))
                fallback = standard_info.get("fallback", params.get("fallback"))
            else:
                context_prompt = params.get("context_prompt")
                fallback = params.get("fallback")

            if agent_type == "resume":
                return analyze_resume(
                    file_path=file_path,
                    job_id=job_id,
                    format_id=format_id or "resume_standard",
                    system_prompt_template=system_prompt_template,
                    context_prompt=context_prompt,
                    fallback=fallback,
                    model_name=model_name,
                    original_filename=job_data.get("original_filename")
                )
            elif agent_type == "report":
                return analyze_report(
                    file_path=file_path,
                    job_id=job_id,
                    format_id=format_id or "report_summary",
                    system_prompt_template=system_prompt_template,
                    context_prompt=context_prompt,
                    fallback=fallback,
                    model_name=model_name,
                    original_filename=job_data.get("original_filename")
                )
            elif agent_type == "other":
                return analyze_generic_document(
                    file_path=file_path,
                    job_id=job_id,
                    format_id=format_id or "generic_document",
                    system_prompt_template=system_prompt_template,
                    context_prompt=context_prompt,
                    fallback=fallback,
                    model_name=model_name,
                    original_filename=job_data.get("original_filename")
                )
            else:
                raise ValueError(f"Unknown document agent type: {agent_type}")

        else:
            raise NotImplementedError(f"Action '{action}' is not supported.")

