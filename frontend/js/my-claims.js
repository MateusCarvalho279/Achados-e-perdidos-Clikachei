/**
 * "Meus Pedidos" — histórico de reivindicações do usuário logado, filtrável
 * por situação e ordenável, resolvido pela procedure `sp_historico_usuario`.
 *
 * É aqui que o aluno reencontra o código de retirada caso feche a aba após a
 * aprovação.
 */

import { api, session } from './api.js';
import { escapeHtml, formatDateTime, renderChrome, showAlert, statusBadge } from './ui.js';

const tbody = document.getElementById('claims-body');
const alertBox = document.querySelector('[data-alert]');
const filterForm = document.getElementById('history-filter');

function row(claim) {
    const pickup = claim.pickup_code
        ? `<code style="font-weight:700;">${escapeHtml(claim.pickup_code)}</code>`
        : '<span style="color:#9a9a9a;">—</span>';

    return `
        <tr>
            <td>
                <span aria-hidden="true">${escapeHtml(claim.icon)}</span>
                ${escapeHtml(claim.item_title)}
            </td>
            <td><code>${escapeHtml(claim.item_code)}</code></td>
            <td>${formatDateTime(claim.created_at)}</td>
            <td>${statusBadge(claim.status)}</td>
            <td>${pickup}</td>
        </tr>
    `;
}

function currentFilters() {
    return {
        status: document.getElementById('h-status').value,
        ordenacao: document.getElementById('h-ordenacao').value,
    };
}

async function load(filters = {}) {
    try {
        const claims = await api.myClaims(filters);
        const hasFilter = Boolean(filters.status);

        if (!claims.length) {
            tbody.innerHTML = `
                <tr><td colspan="5" style="text-align:center;padding:36px;color:#6b6b6b;">
                    ${hasFilter
                        ? 'Nenhum pedido encontrado com esse filtro.'
                        : `Você ainda não reivindicou nenhum item.
                           <a href="index.html" style="color:#6aa012;font-weight:600;">Ver itens disponíveis</a>`}
                </td></tr>`;
            return;
        }

        tbody.innerHTML = claims.map(row).join('');
    } catch (error) {
        tbody.innerHTML = '';
        showAlert(alertBox, error.message);
    }
}

filterForm.addEventListener('submit', (event) => {
    event.preventDefault();
    load(currentFilters());
});

renderChrome('claims');
if (session.requireAuth()) load();
