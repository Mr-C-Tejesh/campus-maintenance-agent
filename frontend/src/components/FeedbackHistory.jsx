import React from 'react';

export default function FeedbackHistory({ history, onRefresh, isLoading }) {
  const formatDate = (isoString) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <section className="ops-card" id="history-panel">
      <div className="card-header">
        <div className="card-title-group">
          <span className="card-label">Recent Persisted Technician Reviews</span>
          <span className="badge badge-neutral">SQLite Audit Trail</span>
        </div>
        <button
          type="button"
          className="btn-secondary"
          onClick={onRefresh}
          disabled={isLoading}
          style={{ fontSize: '11px', padding: '4px 10px' }}
        >
          {isLoading ? 'Refreshing...' : '↻ Refresh Log'}
        </button>
      </div>

      <div className="card-body">
        {history.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '24px 0', fontSize: '13px' }}>
            No technician feedback recorded yet. Reviews submitted above will appear here in chronological order.
          </div>
        ) : (
          <div className="feedback-history-list">
            {history.map((item) => (
              <div key={item.feedback_id || item.id} className="feedback-history-item">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: '100px' }}>
                  <span
                    className={`badge ${
                      item.technician_feedback === 'Correct' ? 'badge-success' : 'badge-critical'
                    }`}
                  >
                    {item.technician_feedback}
                  </span>
                  {item.equipment_type && (
                    <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
                      {item.equipment_type}
                    </span>
                  )}
                </div>

                <div className="fb-complaint-preview" title={item.complaint}>
                  <strong>{item.complaint}</strong>
                  {item.notes && (
                    <span style={{ color: 'var(--text-secondary)', marginLeft: '8px', fontStyle: 'italic' }}>
                      — "{item.notes}"
                    </span>
                  )}
                </div>

                <div className="fb-meta-right">
                  <span style={{ fontFamily: 'monospace', fontSize: '11px' }}>
                    {item.workflow_id ? item.workflow_id.slice(0, 11) : '—'}
                  </span>
                  <span style={{ fontSize: '11px' }}>{formatDate(item.timestamp)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
