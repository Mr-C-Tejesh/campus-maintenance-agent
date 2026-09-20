import React from 'react';

export default function Sidebar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'complaint', label: 'New Complaint', icon: '📝' },
    { id: 'results', label: 'Analysis & Evidence', icon: '🔍' },
    { id: 'feedback', label: 'Technician Review', icon: '✓' },
    { id: 'history', label: 'Audit Feedback Log', icon: '📋' },
  ];

  return (
    <aside className="app-sidebar">
      <div className="sidebar-heading">Campus Operations</div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => setActiveTab(item.id)}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-divider"></div>

      <div className="sidebar-heading">System</div>
      <div className="sidebar-system-info">
        <div><strong>Service:</strong> Decision-Support Agent</div>
        <div style={{ marginTop: '4px' }}><strong>Version:</strong> 1.0.0</div>
        <div style={{ marginTop: '4px' }}><strong>Engine:</strong> ChromaDB + Gemini</div>
      </div>
    </aside>
  );
}
