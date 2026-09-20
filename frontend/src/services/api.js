const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

class ApiError extends Error {
  constructor(message, status = 500, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    let data = null;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    }

    if (!response.ok) {
      let errorMessage = 'An unexpected error occurred.';
      if (data && data.detail) {
        if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        } else if (Array.isArray(data.detail)) {
          // Format FastAPI validation errors
          errorMessage = data.detail
            .map((err) => `${err.loc ? err.loc.join('.') : 'Field'}: ${err.msg}`)
            .join('; ');
        }
      } else if (response.status === 404) {
        errorMessage = 'Requested resource was not found.';
      } else if (response.status === 500) {
        errorMessage = 'Maintenance analysis service encountered an internal error.';
      }

      throw new ApiError(errorMessage, response.status, data);
    }

    return data;
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    // Network or connection failure
    throw new ApiError(
      'Unable to connect to the maintenance service. Please verify the backend is running.',
      0,
      null
    );
  }
}

export const api = {
  /**
   * Checks the health and status of the backend API.
   * @returns {Promise<{ status: string, service: string, version: string }>}
   */
  async checkHealth() {
    return request('/health');
  },

  /**
   * Analyzes a complaint and generates decision support.
   * @param {{ complaint: string, equipment_type?: string, top_k?: number }} params
   * @returns {Promise<any>} WorkflowResult
   */
  async analyzeComplaint({ complaint, equipment_type, location, top_k = 5 }) {
    const payload = {
      complaint: complaint.trim(),
      top_k,
    };
    if (equipment_type && equipment_type !== 'All Equipment') {
      payload.equipment_type = equipment_type;
    }
    if (location && location.trim() !== '') {
      payload.location = location.trim();
    }
    return request('/api/v1/analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },


  /**
   * Submits technician operational feedback for an executed workflow.
   * @param {{ workflow_id: string, feedback: 'Correct' | 'Incorrect', notes?: string }} params
   * @returns {Promise<any>} FeedbackRecord
   */
  async submitFeedback({ workflow_id, feedback, notes }) {
    const payload = {
      workflow_id,
      feedback,
      notes: notes ? notes.trim() : null,
    };
    return request('/api/v1/feedback', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Fetches recent persisted feedback records.
   * @param {number} [limit=10]
   * @returns {Promise<Array<any>>}
   */
  async fetchFeedbackHistory(limit = 10) {
    return request(`/api/v1/feedback?limit=${limit}`);
  },
};
