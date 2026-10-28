/**
 * Fonctions utilitaires partagées entre les pages.
 * Ce fichier doit être chargé AVANT les scripts de page.
 */

// Échapper le HTML pour prévenir les XSS
function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Modale de confirmation générique (Supprimer, etc.)
async function showConfirmDialog(title, message, confirmText = 'Supprimer', cancelText = 'Annuler') {
  return new Promise((resolve) => {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.5);
      z-index: 9999;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 1;
      visibility: visible;
    `;

    modal.innerHTML = `
      <div class="modal-content" style="
        background-color: white;
        border-radius: 8px;
        width: 90%;
        max-width: 500px;
        max-height: 90vh;
        display: flex;
        flex-direction: column;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transform: translateY(0);
        transition: transform 0.3s ease;
      ">
        <div class="modal-header" style="
          padding: 1rem 1.5rem;
          border-bottom: 1px solid #E5E7EB;
          display: flex;
          align-items: center;
          justify-content: space-between;
        ">
          <h3 class="modal-title" style="
            margin: 0;
            font-size: 1.25rem;
            font-weight: 600;
            color: #1F2937;
          ">${escapeHtml(title)}</h3>
          <button type="button" class="close" data-confirm="false" style="
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #6B7280;
            padding: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
          ">&times;</button>
        </div>
        <div class="modal-body" style="
          padding: 1.5rem;
          overflow-y: auto;
          flex: 1;
        ">
          <p style="
            color: #6B7280;
            margin: 0;
            line-height: 1.5;
          ">${escapeHtml(message)}</p>
        </div>
        <div class="modal-footer" style="
          padding: 1rem 1.5rem;
          border-top: 1px solid #E5E7EB;
          display: flex;
          justify-content: flex-end;
          gap: 0.5rem;
        ">
          <button type="button" class="btn btn-secondary" data-confirm="false" style="
            padding: 0.5rem 1rem;
            background-color: #6B7280;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            transition: background-color 0.2s;
          ">${escapeHtml(cancelText)}</button>
          <button type="button" class="btn btn-danger" data-confirm="true" style="
            padding: 0.5rem 1rem;
            background-color: #DC2626;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            transition: background-color 0.2s;
          ">${escapeHtml(confirmText)}</button>
        </div>
      </div>
    `;

    modal.querySelectorAll('button').forEach(button => {
      button.addEventListener('click', () => {
        const confirmed = button.getAttribute('data-confirm') === 'true';
        modal.remove();
        resolve(confirmed);
      });

      if (button.classList.contains('btn-secondary')) {
        button.addEventListener('mouseenter', () => {
          button.style.backgroundColor = '#4B5563';
        });
        button.addEventListener('mouseleave', () => {
          button.style.backgroundColor = '#6B7280';
        });
      } else if (button.classList.contains('btn-danger')) {
        button.addEventListener('mouseenter', () => {
          button.style.backgroundColor = '#B91C1C';
        });
        button.addEventListener('mouseleave', () => {
          button.style.backgroundColor = '#DC2626';
        });
      }
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
        resolve(false);
      }
    });

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        modal.remove();
        document.removeEventListener('keydown', handleEscape);
        resolve(false);
      }
    };
    document.addEventListener('keydown', handleEscape);

    document.body.appendChild(modal);
  });
}
