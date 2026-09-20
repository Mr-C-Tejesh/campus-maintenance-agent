import React from 'react';

export default function Header({ healthStatus, onRefreshHealth }) {
  let statusClass = 'checking';
  let statusText = 'CHECKING STATUS';

  if (healthStatus === 'ok') {
    statusClass = 'operational';
    statusText = 'SYSTEM OPERATIONAL';
  } else if (healthStatus === 'offline') {
    statusClass = 'offline';
    statusText = 'BACKEND OFFLINE';
  }

  return (
    <header className="top-header">
      <div className="header-brand">
        <div className="header-icon" title="Facility Decision Support">
          ⚙
        </div>
        <div className="header-titles">
          <span className="header-title">Maintenance Intelligence</span>
          <span className="header-subtitle">AI-assisted maintenance decision support</span>
        </div>
      </div>

      <div
        className={`header-status ${statusClass}`}
        onClick={onRefreshHealth}
        title="Click to re-check backend service status"
        style={{ cursor: 'pointer' }}
      >
        <span className="status-dot"></span>
        <span>{statusText}</span>
      </div>
    </header>
  );
}
