from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from app.workflow.state import GraphState
from app.workflow.orchestrator import MaintenanceWorkflow

def create_maintenance_graph(workflow: MaintenanceWorkflow) -> StateGraph:
    """
    Constructs a lightweight LangGraph StateGraph mapping 1-to-1 to the maintenance decision workflow.
    Flow: START -> retrieve_node -> diagnose_node -> recommend_node -> END
    """
    def retrieve_node(state: GraphState) -> Dict[str, Any]:
        complaint = state.get("complaint", "")
        equipment_type = state.get("equipment_type")
        try:
            cases = workflow.retriever.search(complaint, equipment_type=equipment_type)
            status = "SUCCESS" if cases else "NO_RELEVANT_CASES"
            return {"retrieved_cases": cases, "workflow_status": status, "error": None}
        except Exception as e:
            return {"retrieved_cases": [], "workflow_status": "RETRIEVAL_FAILED", "error": str(e)}

    def diagnose_node(state: GraphState) -> Dict[str, Any]:
        complaint = state.get("complaint", "")
        equipment_type = state.get("equipment_type")
        cases = state.get("retrieved_cases", [])
        try:
            diag = workflow.diagnosis_service.diagnose(complaint, cases, equipment_type=equipment_type)
            return {"diagnosis": diag}
        except Exception as e:
            return {"diagnosis": None, "error": f"Diagnosis failed: {e}"}

    def recommend_node(state: GraphState) -> Dict[str, Any]:
        complaint = state.get("complaint", "")
        cases = state.get("retrieved_cases", [])
        diag = state.get("diagnosis")
        try:
            rec = workflow.recommendation_service.recommend(complaint, diag, cases)
            return {"recommendation": rec}
        except Exception as e:
            return {"recommendation": None, "error": f"Recommendation failed: {e}"}

    builder = StateGraph(GraphState)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("diagnose", diagnose_node)
    builder.add_node("recommend", recommend_node)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "diagnose")
    builder.add_edge("diagnose", "recommend")
    builder.add_edge("recommend", END)

    return builder.compile()
