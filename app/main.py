import sys
from typing import Optional
from app.workflow import MaintenanceWorkflow

def get_app_status():
    return {"status": "ok", "service": "Campus/Facility Infrastructure Decision-Support Agent"}

def run_workflow_demo(complaint: str, equipment_type: Optional[str] = None):
    """
    Executes a manual end-to-end demonstration of the decision workflow.
    """
    print(f"\n==================================================")
    print(f"Executing Maintenance Workflow Demo")
    print(f"Complaint: '{complaint}'")
    print(f"Equipment Filter: '{equipment_type or 'None'}'")
    print(f"==================================================")

    workflow = MaintenanceWorkflow()
    result = workflow.process_complaint(complaint, equipment_type=equipment_type)

    print(f"\n[WORKFLOW STATUS]: {result.workflow_status}")

    print(f"\n--- [1. RETRIEVAL RESULTS] ---")
    print(f"Retrieved {len(result.retrieved_cases)} historical cases:")
    for c in result.retrieved_cases:
        print(f"  • {c.case_id} ({c.equipment_type}) | Dist: {c.distance:.4f} | Sim: {c.similarity_score:.4f}")
        print(f"    Complaint: {c.complaint}")

    print(f"\n--- [2. DIAGNOSIS RESULT] ---")
    if result.diagnosis:
        print(f"Summary: {result.diagnosis.summary}")
        print(f"Confidence: {result.diagnosis.confidence} | Grounded: {result.diagnosis.grounded}")
        for cause in result.diagnosis.possible_causes:
            print(f"  • Cause: {cause.cause} (Likelihood: {cause.likelihood})")
            print(f"    Supporting Case IDs: {cause.supporting_case_ids}")

    print(f"\n--- [3. RECOMMENDATION RESULT] ---")
    if result.recommendation:
        print(f"Urgency: {result.recommendation.urgency}")
        print(f"Cost Reference: {result.recommendation.estimated_cost.formatted_range} | Median: {result.recommendation.estimated_cost.formatted_reference}")
        print(f"Duration Reference: {result.recommendation.estimated_repair_time.formatted_range} | Median: {result.recommendation.estimated_repair_time.formatted_reference}")
        print(f"Recommended Action: {result.recommendation.recommended_action}")
        print(f"Supporting Case IDs: {result.recommendation.supporting_case_ids}")
        print(f"Technician Checks: {result.recommendation.technician_verification}")
        print(f"Safety Disclaimer: {result.recommendation.safety_disclaimer}")

    if result.error:
        print(f"\n[NOTICE / ERROR]: {result.error}")

    print(f"==================================================\n")
    return result

def main():
    print("Starting Campus/Facility Infrastructure Decision-Support Agent...")
    print(f"Status: {get_app_status()}")
    
    # Run default demo complaint
    sample_complaint = "AC is running continuously but the room remains warm"
    run_workflow_demo(sample_complaint, equipment_type="Air Conditioning")

if __name__ == "__main__":
    main()
