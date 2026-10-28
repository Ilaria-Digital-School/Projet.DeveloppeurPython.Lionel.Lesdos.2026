// frontend/static/js/services/transaction-service.js

import apiService from './api-service';

class TransactionService {
  /**
   * Récupère les transactions avec filtrage
   */
  async getTransactions(filters = {}) {
    try {
      return await apiService.get('/transactions', filters);
    } catch (error) {
      console.error('Erreur lors de la récupération des transactions:', error);
      throw error;
    }
  }

  /**
   * Crée une nouvelle transaction
   */
  async createTransaction(transactionData) {
    try {
      return await apiService.post('/transactions', transactionData);
    } catch (error) {
      console.error('Erreur lors de la création de la transaction:', error);
      throw error;
    }
  }

  // Autres méthodes pour update, delete, etc.
}

export const transactionService = new TransactionService();
