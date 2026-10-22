/**
 * Utilitários de interface compartilhados entre as páginas:
 * escape de HTML, formatação, ícones SVG e montagem da navegação.
 */

import { session } from './api.js';

/* -------------------------------------------------------------------------- */
/* Segurança de renderização                                                   */
/* -------------------------------------------------------------------------- */

/**
 * Escapa texto antes de interpolar em template de HTML.
 * Toda string vinda do backend (título de item, nome de usuário, resposta
 * digitada) passa por aqui — é a defesa contra XSS armazenado.
 */
export function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[&<>"']/g, (char) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    }[char]));
}

/* -------------------------------------------------------------------------- */
/* Formatação                                                                  */
/* -------------------------------------------------------------------------- */

/** ISO (2026-05-04) → pt-BR (04/05/2026), sem sofrer com fuso horário. */
export function formatDate(isoDate) {
    if (!isoDate) return '—';
    const [datePart] = String(isoDate).split('T');
    const [year, month, day] = datePart.split('-');
    if (!year || !month || !day) return isoDate;
    return `${day}/${month}/${year}`;
}

/** Timestamp do SQLite (UTC) → data e hora local legível. */
export function formatDateTime(value) {
    if (!value) return '—';
    const normalized = value.includes('T') ? value : value.replace(' ', 'T') + 'Z';
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString('pt-BR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

export const STATUS_LABELS = {
    available: 'Disponível',
    reserved: 'Reservado',
    claimed: 'Reivindicado',
    archived: 'Arquivado',
    approved: 'Aprovado',
    rejected: 'Recusado',
    pending_review: 'Em análise',
};

export const STATUS_BADGES = {
    available: 'badge--available',
    approved: 'badge--available',
    claimed: 'badge--claimed',
    archived: 'badge--claimed',
    reserved: 'badge--pending',
    pending_review: 'badge--pending',
    rejected: 'badge--rejected',
};

/** `<span class="badge …">Rótulo</span>` para um status conhecido. */
export function statusBadge(status) {
    const label = STATUS_LABELS[status] || status;
    const variant = STATUS_BADGES[status] || 'badge--claimed';
    return `<span class="badge ${variant}">${escapeHtml(label)}</span>`;
}

/* -------------------------------------------------------------------------- */
/* Ícones (SVG inline — sem dependência de fonte de ícones)                     */
/* -------------------------------------------------------------------------- */

export const icons = {
    search: `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4"
                  stroke-linecap="round"><circle cx="11" cy="11" r="7"/>
             <path d="M20 20l-3.6-3.6"/></svg>`,
    calendar: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                    stroke-width="2" stroke-linecap="round">
               <rect x="3" y="5" width="18" height="16" rx="2"/>
               <path d="M8 3v4M16 3v4M3 10h18"/></svg>`,
    hash: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                stroke-width="2" stroke-linecap="round">
           <path d="M9 3L7 21M17 3l-2 18M3.5 8.5h17M3 15.5h17"/></svg>`,
    pin: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 21s7-6.2 7-11a7 7 0 10-14 0c0 4.8 7 11 7 11z"/>
          <circle cx="12" cy="10" r="2.5"/></svg>`,
};

/* -------------------------------------------------------------------------- */
/* Layout                                                                      */
/* -------------------------------------------------------------------------- */

/**
 * Injeta cabeçalho e rodapé nas páginas.
 *
 * A navegação muda conforme a sessão: visitante vê "Portal do Aluno";
 * autenticado vê seus pedidos e o botão de sair; admin ganha o painel.
 *
 * @param {string} active  Identificador da página atual, para destacar o link.
 */
export function renderChrome(active = '') {
    const header = document.querySelector('[data-chrome="header"]');
    const footer = document.querySelector('[data-chrome="footer"]');
    const user = session.user;

    let nav;
    if (user) {
        const initials = user.name
            .split(' ')
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part[0])
            .join('')
            .toUpperCase();

        nav = `
            <a href="index.html" class="${active === 'home' ? 'is-active' : ''}">Itens</a>
            <a href="meus-pedidos.html" class="${active === 'claims' ? 'is-active' : ''}">Meus Pedidos</a>
            ${user.role === 'admin'
                ? `<a href="admin.html" class="${active === 'admin' ? 'is-active' : ''}">Painel Admin</a>`
                : ''}
            <span class="user-chip">
                <span class="user-chip__avatar">${escapeHtml(initials)}</span>
                ${escapeHtml(user.name.split(' ')[0])}
            </span>
            <button type="button" class="link" data-action="logout">Sair</button>
        `;
    } else {
        nav = `
            <a href="index.html" class="${active === 'home' ? 'is-active' : ''}">Itens</a>
            <a href="login.html" class="${active === 'login' ? 'is-active' : ''}">Portal Do Aluno</a>
        `;
    }

    if (header) {
        header.className = 'site-header';
        header.innerHTML = `
            <div class="site-header__inner">
                <a class="brand" href="index.html">
                    <span class="brand__logo">${icons.search}</span>
                    <span>
                        <span class="brand__title">Achados e Perdidos</span><br>
                        <span class="brand__subtitle">Colégio COTEMIG</span>
                    </span>
                </a>
                <nav class="site-nav">${nav}</nav>
            </div>
        `;

        header.querySelector('[data-action="logout"]')?.addEventListener('click', () => {
            session.clear();
            location.href = 'index.html';
        });
    }

    if (footer) {
        footer.className = 'site-footer';
        footer.innerHTML = `
            <div class="container">
                Colégio COTEMIG · Sistema de Achados e Perdidos ·
                Itens não reclamados em 90 dias são doados.
            </div>
        `;
    }
}

/* -------------------------------------------------------------------------- */
/* Feedback                                                                    */
/* -------------------------------------------------------------------------- */

/**
 * Mostra uma mensagem em um contêiner `[data-alert]`.
 * @param {HTMLElement} container
 * @param {string} message
 * @param {'error'|'success'|'warning'} variant
 */
export function showAlert(container, message, variant = 'error') {
    if (!container) return;
    container.innerHTML = `<div class="alert alert--${variant}">${escapeHtml(message)}</div>`;
    container.classList.remove('hidden');
}

export function clearAlert(container) {
    if (!container) return;
    container.innerHTML = '';
    container.classList.add('hidden');
}

/** Alterna um botão para o estado "carregando", devolvendo a função de reset. */
export function setLoading(button, loadingLabel = 'Aguarde…') {
    if (!button) return () => {};
    const original = button.innerHTML;
    button.disabled = true;
    button.innerHTML = loadingLabel;
    return () => {
        button.disabled = false;
        button.innerHTML = original;
    };
}
