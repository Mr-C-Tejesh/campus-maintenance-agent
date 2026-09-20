import React, { useState } from 'react';

export default function FeedbackPanel({
  workflowId,
  onSubmitFeedback,
  isSubmitting,
  isSubmitted,
  submittedValue,
  conflictError,
  error,
}) {
  const [feedbackChoice, setFeedbackChoice] = useState('');
  const [notes, setNotes] = useState('');

  if (!workflowId) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!feedbackChoice || isSubmitting || isSubmitted) return;
    onSubmitFeedback({
      workflow_id: workflowId,
      feedback: feedbackChoice,
      notes,
    });
  };

  return (
    <section className="ops-card feedback-card" id="feedback-panel">
      <div className="card-header">
        <div className="card-title-group">
          <span className="card-label">Technician Review & Feedback</span>
          <span className="badge badge-amber">Compulsory Loop</span>
        </div>
        <span className="badge badge-neutral">Workflow: {workflowId}</span>
      </div>

      <div className="card-body">
        {isSubmitted ? (
          <div className="feedback-success-msg">
            <span>✓</span>
            <span>
              Feedback submitted successfully: Marked as <strong>{submittedValue}</strong>. Persisted to operational SQLite audit store.
            </span>
          </div>
        ) : conflictError ? (
          <div className="feedback-conflict-msg">
            ⚠️ {conflictError}
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="review-prompt">
              Was this diagnosis and recommendation operationally sound?
            </div>

            <div className="feedback-btn-group">
              <button
                type="button"
                className={`btn-choice ${feedbackChoice === 'Correct' ? 'selected-correct' : ''}`}
                onClick={() => setFeedbackChoice('Correct')}
                disabled={isSubmitting}
              >
                <span>✓</span>
                <span>CORRECT</span>
              </button>

              <button
                type="button"
                className={`btn-choice ${feedbackChoice === 'Incorrect' ? 'selected-incorrect' : ''}`}
                onClick={() => setFeedbackChoice('Incorrect')}
                disabled={isSubmitting}
              >
                <span>✕</span>
                <span>INCORRECT</span>
              </button>
            </div>

            <div className="form-group" style={{ marginBottom: '14px' }}>
              <label htmlFor="tech-notes" className="form-label">
                Technician Field Observations / Notes (Optional)
              </label>
              <textarea
                id="tech-notes"
                className="form-textarea"
                placeholder="Add technician verification notes, adjustments made on-site, or reason for disagreement..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                disabled={isSubmitting}
                maxLength={1000}
              />
            </div>

            {error && (
              <div
                style={{
                  marginBottom: '14px',
                  padding: '10px 12px',
                  backgroundColor: 'var(--status-critical-bg)',
                  border: '1px solid var(--status-critical-border)',
                  color: 'var(--status-critical)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '12px',
                }}
              >
                {error}
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="submit"
                className="btn-primary"
                disabled={!feedbackChoice || isSubmitting}
                style={{
                  backgroundColor:
                    feedbackChoice === 'Correct'
                      ? 'var(--status-success)'
                      : feedbackChoice === 'Incorrect'
                      ? 'var(--status-critical)'
                      : 'var(--accent-primary)',
                  borderColor: 'transparent',
                }}
              >
                {isSubmitting ? 'SAVING REVIEW...' : 'SUBMIT OPERATIONAL REVIEW'}
              </button>
            </div>
          </form>
        )}
      </div>
    </section>
  );
}
