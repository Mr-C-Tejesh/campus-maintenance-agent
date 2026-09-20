import React, { useState } from 'react';

export default function AnalysisView({ result }) {
  const [expandedCaseId, setExpandedCaseId] = useState(null);

  if (!result) return null;

  const {
    workflow_id,
    workflow_status,
    complaint,
    equipment_type,
    location,
    retrieved_cases = [],
    diagnosis,
    recommendation,
    error,
  } = result;

  const toggleCaseExpand = (caseId) => {
    setExpandedCaseId((prev) => (prev === caseId ? null : caseId));
  };

  // Confidence badge helper
  const getConfidenceBadge = (confidence) => {
    const conf = (confidence || '').toLowerCase();
    if (conf === 'high') return <span className="badge badge-success">High Confidence</span>;
    if (conf === 'medium') return <span className="badge badge-warning">Medium Confidence</span>;
    return <span className="badge badge-neutral">Low Confidence</span>;
  };

  // Urgency badge helper
  const getUrgencyBadge = (urgency) => {
    const urg = (urgency || '').toLowerCase();
    if (urg === 'critical') return <span className="badge badge-critical">Critical Urgency</span>;
    if (urg === 'high') return <span className="badge badge-warning">High Urgency</span>;
    if (urg === 'medium') return <span className="badge badge-amber">Medium Urgency</span>;
    return <span className="badge badge-success">Low Urgency</span>;
  };

  const safeRetrievedCases = Array.isArray(retrieved_cases) ? retrieved_cases : [];
  const isNoRelevantCases =
    workflow_status === 'NO_RELEVANT_CASES' || (safeRetrievedCases.length === 0 && !error);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Workflow Metadata Bar */}
      <div className="workflow-status-bar">
        <div className="wf-meta">
          <span>Workflow Execution: <span className="wf-id">{workflow_id || 'N/A'}</span></span>
          <span>Status: <strong style={{ color: 'var(--text-primary)' }}>{workflow_status}</strong></span>
          {equipment_type && <span>Category: {equipment_type}</span>}
          {location && <span>Facility: {location}</span>}
        </div>
        {diagnosis && diagnosis.grounded !== undefined && (
          <span className={`badge ${diagnosis.grounded ? 'badge-success' : 'badge-warning'}`}>
            {diagnosis.grounded ? '● Grounded in Historical Evidence' : '○ Ungrounded'}
          </span>
        )}
      </div>


      {/* 1. DIAGNOSIS (AI Analysis) */}
      {diagnosis && (
        <section className="ops-card diagnosis-panel" id="diagnosis-section">
          <div className="card-header">
            <div className="card-title-group">
              <span className="card-label">Diagnosis & Root-Cause Assessment</span>
              <span className="badge badge-info">AI Inference</span>
            </div>
            {getConfidenceBadge(diagnosis.confidence)}
          </div>

          <div className="card-body">
            <div className="diagnosis-summary">
              {diagnosis.summary}
            </div>

            {diagnosis.possible_causes && diagnosis.possible_causes.length > 0 && (
              <div style={{ marginBottom: '14px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.5px' }}>
                  Identified Potential Causes
                </div>
                <div className="causes-grid">
                  {diagnosis.possible_causes.map((pc, idx) => (
                    <div key={idx} className="cause-item">
                      <div className="cause-header">
                        <span className="cause-title">{pc.cause}</span>
                        <span className={`badge ${pc.likelihood === 'High' ? 'badge-warning' : 'badge-neutral'}`}>
                          {pc.likelihood} Likelihood
                        </span>
                      </div>
                      <div className="cause-explanation">{pc.explanation}</div>
                      {pc.supporting_case_ids && pc.supporting_case_ids.length > 0 && (
                        <div className="cause-support">
                          Supporting Cases: {pc.supporting_case_ids.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {diagnosis.reasoning && (
              <div>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '6px', letterSpacing: '0.5px' }}>
                  Reasoning Trace
                </div>
                <div className="reasoning-box">
                  {diagnosis.reasoning}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* 2. HISTORICAL EVIDENCE (Data Records) */}
      <section className="ops-card" id="evidence-section">
        <div className="card-header">
          <div className="card-title-group">
            <span className="card-label">Historical Maintenance Evidence</span>
            <span className="badge badge-neutral">ChromaDB Vector Store</span>
          </div>
          <span className="badge badge-neutral">
            {safeRetrievedCases.length} Match{safeRetrievedCases.length === 1 ? '' : 'es'}
          </span>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          {isNoRelevantCases ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                NO RELEVANT HISTORICAL CASES
              </div>
              <p style={{ fontSize: '13px' }}>
                No sufficiently relevant historical maintenance records were retrieved for this complaint.
              </p>
            </div>
          ) : (
            <table className="evidence-table">
              <thead>
                <tr>
                  <th style={{ width: '110px' }}>Case ID</th>
                  <th>Equipment</th>
                  <th style={{ width: '100px' }}>Similarity</th>
                  <th>Observed Complaint</th>
                  <th>Historical Root Cause</th>
                  <th style={{ width: '80px', textAlign: 'center' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {safeRetrievedCases.map((c) => {

                  const isExpanded = expandedCaseId === c.case_id;
                  const similarityPct = Math.round((c.similarity_score || 0) * 100);

                  return (
                    <React.Fragment key={c.case_id}>
                      <tr
                        className={`evidence-row ${isExpanded ? 'expanded' : ''}`}
                        onClick={() => toggleCaseExpand(c.case_id)}
                      >
                        <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{c.case_id}</td>
                        <td>{c.equipment_type}</td>
                        <td>
                          <span
                            className={`badge ${similarityPct >= 65 ? 'badge-success' : 'badge-amber'}`}
                            style={{ fontVariantNumeric: 'tabular-nums' }}
                          >
                            {similarityPct}%
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-secondary)' }}>{c.complaint}</td>
                        <td style={{ fontWeight: 500 }}>{c.root_cause || '—'}</td>
                        <td style={{ textAlign: 'center', color: 'var(--accent-primary)', fontWeight: 600 }}>
                          {isExpanded ? '▲ Hide' : '▼ View'}
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr>
                          <td colSpan={6} style={{ padding: 0, backgroundColor: 'transparent' }}>
                            <div className="case-detail-box">
                              <div className="detail-grid">
                                <div>
                                  <div className="detail-item-label">Equipment Model</div>
                                  <div className="detail-item-val">{c.equipment_model || 'Standard'}</div>
                                </div>
                                <div>
                                  <div className="detail-item-label">Facility Location</div>
                                  <div className="detail-item-val">{c.location || 'Campus Wide'}</div>
                                </div>
                                <div>
                                  <div className="detail-item-label">Date Reported</div>
                                  <div className="detail-item-val">{c.date_reported || 'Recorded'}</div>
                                </div>
                                <div>
                                  <div className="detail-item-label">Historical Action Taken</div>
                                  <div className="detail-item-val">{c.action_taken || 'Repaired'}</div>
                                </div>
                                <div>
                                  <div className="detail-item-label">Historical Repair Cost</div>
                                  <div className="detail-item-val" style={{ fontWeight: 600 }}>
                                    ₹{Number(c.repair_cost || 0).toLocaleString()}
                                  </div>
                                </div>
                                <div>
                                  <div className="detail-item-label">Historical Repair Time</div>
                                  <div className="detail-item-val" style={{ fontWeight: 600 }}>
                                    {c.repair_time_hours} Hours
                                  </div>
                                </div>
                                <div style={{ gridColumn: 'span 3' }}>
                                  <div className="detail-item-label">Recorded Symptoms</div>
                                  <div className="detail-item-val">{c.symptoms || 'None specified'}</div>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* 3. RECOMMENDED ACTION (Decision Support Panel) */}
      {recommendation && (
        <section className="ops-card recommendation-panel" id="recommendation-section">
          <div className="card-header">
            <div className="card-title-group">
              <span className="card-label">Recommended Maintenance Action</span>
              <span className="badge badge-amber">Decision Support</span>
            </div>
            {getUrgencyBadge(recommendation.urgency)}
          </div>

          <div className="card-body">
            <div className="rec-action-text">
              {recommendation.recommended_action}
            </div>

            {/* Metrics Row: Cost Reference, Time Reference, Urgency */}
            <div className="metrics-row">
              <div className="metric-card">
                <div className="metric-label">Historical Cost Reference</div>
                <div className="metric-value">
                  {recommendation.estimated_cost?.formatted_range || '—'}
                </div>
                <div className="metric-sub">
                  Median: {recommendation.estimated_cost?.formatted_reference || '—'}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Historical Repair-Time Reference</div>
                <div className="metric-value">
                  {recommendation.estimated_repair_time?.formatted_range || '—'}
                </div>
                <div className="metric-sub">
                  Median: {recommendation.estimated_repair_time?.formatted_reference || '—'}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Operational Urgency</div>
                <div className="metric-value" style={{ textTransform: 'uppercase' }}>
                  {recommendation.urgency}
                </div>
                <div className="metric-sub">
                  Deterministic facility rule
                </div>
              </div>
            </div>

            {/* 4. TECHNICIAN VERIFICATION STEPS */}
            {recommendation.technician_verification && recommendation.technician_verification.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.5px' }}>
                  Technician Verification Checklist
                </div>
                <div className="checklist">
                  {recommendation.technician_verification.map((step, idx) => (
                    <div key={idx} className="check-item">
                      <span className="check-icon">✓</span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Safety Disclaimer */}
            <div className="disclaimer-banner">
              <strong>DECISION SUPPORT ONLY:</strong> {recommendation.safety_disclaimer || 'Physical inspection by a qualified technician is required before performing repairs.'}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
