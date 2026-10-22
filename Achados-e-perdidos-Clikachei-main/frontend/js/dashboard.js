/**
 * Dashboard público — galeria dos itens encontrados, com busca avançada.
 *
 * A busca (texto + categoria + intervalo de datas + ordenação) é resolvida
 * inteiramente no backend pela procedure `sp_buscar_itens` — este arquivo só
 * monta a query string e renderiza o que a API devolve. Não existe caminho no
 * código capaz de exibir uma característica sigilosa aqui: o backend
 * simplesmente não a envia.
 */

import { api } from './api.js';
import { escapeHtml, formatDate, icons, renderChrome, showAlert, statusBadge } from './ui.js';

const grid = document.getElementById('item-grid');
const counter = document.getElementById('items-count');
const alertBox = document.querySelector('[data-alert]');
const form = document.getElementById('search-form');
const categoriaSelect = document.getElementById('f-categoria');

/** Monta o cartão de um item, no mesmo layout da referência visual. */
function itemCard(item) {
    const code = escapeHtml(item.public_code);
    const location = item.found_location
        ? `<span>${icons.pin}${escapeHtml(item.found_location)}</span>`
        : '';

    return `
        <article class="item-card">
            <div class="item-card__media">
                <div class="item-card__icon" aria-hidden="true">${escapeHtml(item.icon)}</div>
            </div>
            <div class="item-card__body">
                <div class="item-card__head">
                    <h3 class="item-card__title">${escapeHtml(item.title)}</h3>
                    ${statusBadge(item.status)}
                </div>
                <div class="item-card__meta">
                    <span>${icons.calendar}Encontrado em ${formatDate(item.found_date)}</span>
                    <span>${icons.hash}<code>${code}</code></span>
                    ${location}
                </div>
                <a class="btn btn--block" href="reivindicar.html?item=${encodeURIComponent(item.public_code)}">
                    Ver Detalhes
                </a>
            </div>
        </article>
    `;
}

function emptyState(message) {
    grid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
            <div class="empty-state__icon" aria-hidden="true">📭</div>
            <h3>${escapeHtml(message)}</h3>
            <p>Tente ajustar os filtros de busca.</p>
        </div>
    `;
}

/** Preenche o `<select>` de categoria a partir dos itens já carregados. */
function populateCategories(items) {
    const current = categoriaSelect.value;
    const categories = [...new Set(items.map((item) => item.category))].sort((a, b) =>
        a.localeCompare(b, 'pt-BR'));

    categoriaSelect.innerHTML = '<option value="">Todas</option>' +
        categories.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    categoriaSelect.value = current;
}

function currentFilters() {
    return {
        texto: document.getElementById('f-texto').value.trim(),
        categoria: categoriaSelect.value,
        data_inicio: document.getElementById('f-data-inicio').value,
        data_fim: document.getElementById('f-data-fim').value,
        ordenacao: document.getElementById('f-ordenacao').value,
    };
}

async function loadItems(filters = {}, { keepCategories = false } = {}) {
    try {
        const items = await api.listItems(filters);
        const hasFilters = Object.values(filters).some(Boolean);

        if (!keepCategories) populateCategories(items);

        if (!items.length) {
            counter.textContent = hasFilters
                ? 'Nenhum item encontrado com esses filtros'
                : 'Nenhum item disponível no momento';
            emptyState(hasFilters ? 'Nenhum item corresponde à busca' : 'Nenhum item aguardando identificação');
            return;
        }

        counter.textContent = `${items.length} ${items.length === 1
            ? 'item aguardando identificação'
            : 'itens aguardando identificação'}`;
        grid.innerHTML = items.map(itemCard).join('');
    } catch (error) {
        counter.textContent = 'Não foi possível carregar os itens';
        grid.innerHTML = '';
        showAlert(alertBox, error.message);
    }
}

form.addEventListener('submit', (event) => {
    event.preventDefault();
    loadItems(currentFilters(), { keepCategories: true });
});

document.getElementById('search-clear').addEventListener('click', () => {
    form.reset();
    loadItems({}, { keepCategories: true });
});

renderChrome('home');
loadItems();
