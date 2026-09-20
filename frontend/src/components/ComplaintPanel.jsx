import React from 'react';

const DATASET_LOCATIONS = [
  'Academic Block A',
  'Academic Block B',
  'Administrative Block',
  'Auditorium',
  'Hostel Block',
  'Laboratory Block',
  'Library',
  'Parking Area',
  'Sports Complex',
  'Workshop',
];

const EXAMPLE_COMPLAINTS = [
  {
    text: 'AC is running continuously but the room remains warm',
    equipment: 'Air Conditioning',
    location: 'Laboratory Block',
  },
  {
    text: 'Generator failed to start during a power outage',
    equipment: 'Generator',
    location: 'Administrative Block',
  },
  {
    text: 'Elevator door is not closing completely',
    equipment: 'Elevator',
    location: 'Academic Block A',
  },
];

export default function ComplaintPanel({
  complaint,
  setComplaint,
  equipmentType,
  setEquipmentType,
  location,
  setLocation,
  onAnalyze,
  isLoading,
  error,
}) {
  const handleExampleClick = (example) => {
    setComplaint(example.text);
    setEquipmentType(example.equipment);
    setLocation(example.location);
  };

  const isFormValid = complaint.trim().length >= 3;

  return (
    <section className="ops-card" id="complaint-panel">
      <div className="card-header">
        <div className="card-title-group">
          <span className="card-label">Log Complaint</span>
          <span className="badge badge-neutral">Intake</span>
        </div>
      </div>

      <div className="card-body">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (isFormValid && !isLoading) {
              onAnalyze();
            }
          }}
        >
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="equipment-type" className="form-label">
                Equipment Category
              </label>
              <select
                id="equipment-type"
                className="form-select"
                value={equipmentType}
                onChange={(e) => setEquipmentType(e.target.value)}
                disabled={isLoading}
              >
                <option value="">All Categories (Auto-detect)</option>
                <option value="Air Conditioning">Air Conditioning</option>
                <option value="Generator">Generator</option>
                <option value="Elevator">Elevator</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="facility-location" className="form-label">
                Facility Location (Dataset Reference)
              </label>
              <select
                id="facility-location"
                className="form-select"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                disabled={isLoading}
              >
                <option value="">Campus Facility (Optional)</option>
                {DATASET_LOCATIONS.map((loc) => (
                  <option key={loc} value={loc}>
                    {loc}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="complaint-desc" className="form-label">
              Complaint Description <span style={{ color: 'var(--status-critical)' }}>*</span>
            </label>
            <textarea
              id="complaint-desc"
              className="form-textarea"
              placeholder="Describe symptoms, strange noises, operational failures, or error codes observed on-site..."
              value={complaint}
              onChange={(e) => setComplaint(e.target.value)}
              rows={3}
              disabled={isLoading}
              maxLength={1000}
            />
            <div className="textarea-footer">
              <span>Min. 3 characters required</span>
              <span>{complaint.length} / 1000</span>
            </div>
          </div>

          <div className="example-chips">
            <span className="chip-label">Suggestions:</span>
            {EXAMPLE_COMPLAINTS.map((ex, idx) => (
              <button
                key={idx}
                type="button"
                className="example-chip"
                onClick={() => handleExampleClick(ex)}
                disabled={isLoading}
                title={`Select example: ${ex.equipment}`}
              >
                {ex.text}
              </button>
            ))}
          </div>

          {error && (
            <div
              style={{
                marginTop: '16px',
                padding: '10px 14px',
                backgroundColor: 'var(--status-critical-bg)',
                border: '1px solid var(--status-critical-border)',
                color: 'var(--status-critical)',
                borderRadius: 'var(--radius-md)',
                fontSize: '12px',
                fontWeight: 500,
              }}
            >
              {error}
            </div>
          )}

          <div style={{ marginTop: '18px', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              type="submit"
              className="btn-primary"
              disabled={!isFormValid || isLoading}
            >
              {isLoading ? (
                <>
                  <span className="spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }}></span>
                  <span>ANALYZING COMPLAINT...</span>
                </>
              ) : (
                <>
                  <span>ANALYZE COMPLAINT</span>
                  <span>→</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
