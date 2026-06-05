import os
import sys
import json
import unittest

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from workflow_runner import WorkflowRunner


class TestWorkflowRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = WorkflowRunner()
        os.makedirs("downloads", exist_ok=True)
        
        # Create a mock resume file
        cls.mock_resume_path = "downloads/mock_resume.txt"
        with open(cls.mock_resume_path, "w", encoding="utf-8") as f:
            f.write("Candidate: John Doe\nRole: Python Developer\nExperience: 5 years\nSkills: Python, FastAPI, SQL")

        # Create a mock report file
        cls.mock_report_path = "downloads/mock_report.txt"
        with open(cls.mock_report_path, "w", encoding="utf-8") as f:
            f.write("Q3 Financial Report\nSummary: Revenue grew by 15%\nRisks: Supply chain issues")

    def test_resume_workflow(self):
        print("\n=== Running Resume Workflow Test ===")
        job_data = {
            "job_id": "test_resume",
            "file_path": self.mock_resume_path,
            "format_id": "resume_standard",
            "agent_type": "resume"
        }
        
        result = self.runner.run_workflow("resume", job_data)
        print("Resume workflow result:")
        print(json.dumps(result, indent=2))
        
        # Verify result format and fallback/mock score
        self.assertIn("overall_score", result)
        self.assertEqual(result["overall_score"], 72)
        self.assertIn("technical_skills", result)
        self.assertTrue(os.path.exists("result_test_resume.json"))

    def test_resume_workflow_with_golden_standard(self):
        print("\n=== Running Resume Workflow with Software Engineer Standard Test ===")
        job_data = {
            "job_id": "test_resume_se",
            "file_path": self.mock_resume_path,
            "format_id": "resume_standard",
            "agent_type": "resume",
            "golden_standard": "software_engineer"
        }
        
        result = self.runner.run_workflow("resume", job_data)
        print("Resume software engineer workflow result:")
        print(json.dumps(result, indent=2))
        
        # Verify result format and fallback/mock score for software engineer standard
        self.assertIn("overall_score", result)
        self.assertEqual(result["overall_score"], 90)
        self.assertIn("technical_skills", result)
        self.assertIn("Go", result["technical_skills"])
        self.assertTrue(os.path.exists("result_test_resume_se.json"))

    def test_report_workflow(self):
        print("\n=== Running Report Workflow Test ===")
        job_data = {
            "job_id": "test_report",
            "file_path": self.mock_report_path,
            "format_id": "report_summary",
            "agent_type": "report"
        }
        
        result = self.runner.run_workflow("report", job_data)
        print("Report workflow result:")
        print(json.dumps(result, indent=2))
        
        # Verify result format and fallback/mock score
        self.assertIn("summary", result)
        self.assertIn("confidence_score", result)
        self.assertEqual(result["confidence_score"], 85)
        self.assertTrue(os.path.exists("result_test_report.json"))

    def test_generic_workflow_routing(self):
        print("\n=== Running Generic Workflow Classification Test ===")
        # Test 1: Classify resume file
        resume_job_data = {
            "job_id": "test_generic_resume",
            "file_path": self.mock_resume_path,
            "agent_type": "generic"
        }
        res = self.runner.run_workflow("generic", resume_job_data)
        print(f"Generic Resume Classification result: {res}")
        self.assertEqual(res.get("classification"), "resume")
        
        # Test 2: Classify report file
        report_job_data = {
            "job_id": "test_generic_report",
            "file_path": self.mock_report_path,
            "agent_type": "generic"
        }
        res = self.runner.run_workflow("generic", report_job_data)
        print(f"Generic Report Classification result: {res}")
        self.assertEqual(res.get("classification"), "report")

    def test_video_workflow_local(self):
        print("\n=== Running Video Workflow Test ===")
        # Look for local video_t1.mp4 or standard plumbing.mp4
        local_video = "downloads/video_t1.mp4"
        if not os.path.exists(local_video):
            # Fallback to golden dataset video
            local_video = "../golden_dataset/good/plumbing.mp4"

        if not os.path.exists(local_video):
            print("Skipping local video test: video file not found.")
            return

        job_data = {
            "job_id": "test_video",
            "video_path": local_video,
            "format_id": "video_training_default",
            "agent_type": "video",
            "golden_standard": "plumbing"
        }

        result = self.runner.run_workflow("video", job_data)
        print("Video workflow result:")
        print(json.dumps(result, indent=2))

        # Verify output keys
        self.assertIn("skill_score", result)
        self.assertIn("safety_violations", result)
        self.assertEqual(result["skill_score"], 78)
        self.assertTrue(os.path.exists("result_test_video.json"))

    @classmethod
    def tearDownClass(cls):
        # Clean up mock files and result files
        for f in [cls.mock_resume_path, cls.mock_report_path, "result_test_resume.json", "result_test_resume_se.json", "result_test_report.json", "result_test_video.json"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
