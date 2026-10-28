// frontend/static/js/services/api-service.js

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/**
 * Service centralisé pour les appels API
 */
class ApiService {
  constructor(baseURL = '') {
    this.baseURL = baseURL;
  }

  /**
   * Gestion générique des réponses
   */
  async _handleResponse(response) {
    const data = await response.json().catch(() => ({}));
    
    if (!response.ok) {
      const error = new ApiError(
        data.message || 'Une erreur est survenue',
        response.status
      );
      throw error;
    }
    
    return data;
  }

  /**
   * Effectue une requête GET
   */
  async get(endpoint, params = {}) {
    const url = new URL(`${this.baseURL}${endpoint}`, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, value);
      }
    });

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      credentials: 'same-origin'
    });

    return this._handleResponse(response);
  }

  /**
   * Effectue une requête POST
   */
  async post(endpoint, data = {}) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-CSRF-Token': this._getCSRFToken()
      },
      body: JSON.stringify(data),
      credentials: 'same-origin'
    });

    return this._handleResponse(response);
  }

  /**
   * Récupère le token CSRF
   */
  _getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  }
}

// Instance unique du service
const apiService = new ApiService('/api/v1');

export default apiService;
