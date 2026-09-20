import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ComplaintPanel from './components/ComplaintPanel';
import AnalysisView from './components/AnalysisView';
import FeedbackPanel from './components/FeedbackPanel';
import FeedbackHistory from './components/FeedbackHistory';
import { api } from './services/api';

export default function App() {
  // Navigation
  const [activeTab, setActiveTab] = useState('complaint');

  // Backend Health
  const [healthStatus, setHealthStatus] = useState('checking');

  // Complaint Form
  const [complaint, setComplaint] = useState('');
  const [equipmentType, setEquipmentType] = useState('');
  const [location, setLocation] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);

  // Workflow Analysis Result
  const [analysisResult, setAnalysisResult] = useState(null);

  // Technician Feedback State
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [submittedFeedbackValue, setSubmittedFeedbackValue] = useState('');
  const [feedbackConflict, setFeedbackConflict] = useState(null);
  const [feedbackError, setFeedbackError] = useState(null);

  // Feedback History Log
  const [feedbackHistory, setFeedbackHistory] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Check Health
  const checkHealth = useCallback(async () => {
    try {
      setHealthStatus('checking');
      const res = await api.checkHealth();
      if (res && res.status === 'ok') {
        setHealthStatus('ok');
      } else {
        setHealthStatus('offline');
      }
    } catch {
      setHealthStatus('offline');
    }
  }, []);

  // Fetch Feedback History
  const loadFeedbackHistory = useCallback(async () => {
    try {
      setIsLoadingHistory(true);
      const data = await api.fetchFeedbackHistory(25);
      setFeedbackHistory(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load feedback history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  // Initial mount
  useEffect(() => {
    checkHealth();
    loadFeedbackHistory();
  }, [checkHealth, loadFeedbackHistory]);

  // Handle Analyze Submission
  const handleAnalyze = async () => {
    if (!complaint.trim() || isAnalyzing) return;

    setIsAnalyzing(true);
    setAnalysisError(null);
    setAnalysisResult(null);

    // Reset feedback state for new analysis run
    setFeedbackSubmitted(false);
    setSubmittedFeedbackValue('');
    setFeedbackConflict(null);
    setFeedbackError(null);

    try {
      const result = await api.analyzeComplaint({
        complaint: complaint.trim(),
        equipment_type: equipmentType || undefined,
        top_k: 5,
      });

      setAnalysisResult(result);
      setActiveTab('results');

      // Scroll smoothly to results
      setTimeout(() => {
        const resultsEl = document.getElementById('results-section');
        if (resultsEl) {
          resultsEl.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);
    } catch (err) {
      setAnalysisError(err.message || 'Complaint analysis could not be completed.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle Feedback Submission
  const handleSubmitFeedback = async ({ workflow_id, feedback, notes }) => {
    setIsSubmittingFeedback(true);
    setFeedbackConflict(null);
    setFeedbackError(null);

    try {
      await api.submitFeedback({
        workflow_id,
        feedback,
        notes,
      });

      setFeedbackSubmitted(true);
      setSubmittedFeedbackValue(feedback);
      // Refresh audit history
      loadFeedbackHistory();
    } catch (err) {
      if (err.status === 409) {
        setFeedbackConflict(err.message || 'Feedback has already been submitted for this workflow execution.');
      } else {
        setFeedbackError(err.message || 'Feedback could not be saved. Please try again.');
      }
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    let targetId = null;
    if (tabId === 'complaint') targetId = 'complaint-panel';
    else if (tabId === 'results') targetId = 'results-section';
    else if (tabId === 'feedback') targetId = 'feedback-panel';
    else if (tabId === 'history') targetId = 'history-panel';

    if (targetId) {
      const el = document.getElementById(targetId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <div className="app-container">
      <Header healthStatus={healthStatus} onRefreshHealth={checkHealth} />

      <div className="app-body">
        <Sidebar activeTab={activeTab} setActiveTab={handleTabChange} />

        <main className="main-content">
          <div className="content-wrapper">
            {/* 1. Intake Complaint Form */}
            <ComplaintPanel
              complaint={complaint}
              setComplaint={setComplaint}
              equipmentType={equipmentType}
              setEquipmentType={setEquipmentType}
              location={location}
              setLocation={setLocation}
              onAnalyze={handleAnalyze}
              isLoading={isAnalyzing}
              error={analysisError}
            />

            {/* 2. Loading State */}
            {isAnalyzing && (
              <div className="ops-card loading-card">
                <div className="spinner"></div>
                <div className="loading-title">Analyzing Complaint</div>
                <div className="loading-steps">
                  <span>Searching historical maintenance records in ChromaDB...</span>
                  <span>Evaluating grounded causes and similarity thresholds...</span>
                  <span>Formulating maintenance decision-support plan...</span>
                </div>
              </div>
            )}

            {/* 3. Empty State (Before Analysis) */}
            {!isAnalyzing && !analysisResult && (
              <div className="empty-state">
                <div className="empty-icon">⚙</div>
                <div className="empty-title">Awaiting Complaint Intake</div>
                <p className="empty-text">
                  Submit a maintenance complaint above to retrieve similar historical cases from the campus archive and generate grounded decision support.
                </p>
              </div>
            )}

            {/* 4. Results Section: Diagnosis, Evidence, Recommendation */}
            {!isAnalyzing && analysisResult && (
              <div id="results-section">
                <AnalysisView result={analysisResult} />
              </div>
            )}

            {/* 5. Technician Feedback Panel */}
            {!isAnalyzing && analysisResult && analysisResult.workflow_id && (
              <FeedbackPanel
                workflowId={analysisResult.workflow_id}
                onSubmitFeedback={handleSubmitFeedback}
                isSubmitting={isSubmittingFeedback}
                isSubmitted={feedbackSubmitted}
                submittedValue={submittedFeedbackValue}
                conflictError={feedbackConflict}
                error={feedbackError}
              />
            )}

            {/* 6. Recent Feedback Audit Log */}
            <FeedbackHistory
              history={feedbackHistory}
              onRefresh={loadFeedbackHistory}
              isLoading={isLoadingHistory}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
