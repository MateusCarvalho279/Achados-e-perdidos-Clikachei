/**
 * Painel administrativo.
 *
 * Três painéis: itens registrados, cadastro de item (com gabarito) e curadoria
 * das reivindicações. O backend já exige perfil admin em todas as rotas usadas
 * aqui — a verificação no cliente é apenas de conveniência.
 */

import { api, session } from './api.js';
import {
    clearAlert, escapeHtml, formatDate, formatDateTime, renderChrome, setLoading,
    showAlert, statusBadge,
} from './ui.js';

const alertBox = document.querySelector('[data-alert]');
const statsEl = document.getElementById('stats');
const itemsBody = document.getElementById('items-body');
const claimsList = document.getElementById('claims-list');
const attributesEl = document.getElementById('attributes');
const itemForm = document.getElementById('item-form');
const statusFilter = document.getElementById('claims-status-filter');
const reportCategoriesBody = document.getElementById('report-categories-body');
const reportLocationsBody = document.getElementById('report-locations-body');

/* -------------------------------------------------------------------------- */
/* Navegação por abas                                                          */
/* -------------------------------------------------------------------------- */

document.querySelectorAll('[data-panel]').forEach((tab) => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('[data-panel]').forEach((other) =>
            other.classList.toggle('is-active', other === tab));
        document.querySelectorAll('[data-panel-content]').forEach((panel) =>
            panel.classList.toggle('hidden', panel.dataset.panelContent !== tab.dataset.panel));
    });
});

/* -------------------------------------------------------------------------- */
/* Indicadores                                                                 */
/* -------------------------------------------------------------------------- */

async function loadStats() {
    try {
        const stats = await api.adminStats();
        const cards = [
            ['Disponíveis', stats.items_available],
            ['Devolvidos', stats.items_claimed],
            ['Reivindicações', stats.claims_total],
            ['Em análise', stats.claims_pending],
            ['Usuários', stats.users_total],
        ];
        statsEl.innerHTML = cards.map(([label, value]) => `
            <div class="stat">
                <div class="stat__value">${value}</div>
                <div class="stat__label">${label}</div>
            </div>
        `).join('');
    } catch (error) {
        showAlert(alertBox, error.message);
    }
}

/* -------------------------------------------------------------------------- */
/* Itens                                                                       */
/* -------------------------------------------------------------------------- */

async function loadItems() {
    try {
        const items = await api.adminItems();

        if (!items.length) {
            itemsBody.innerHTML = '<tr><td colspan="7">Nenhum item cadastrado.</td></tr>';
            return;
        }

        itemsBody.innerHTML = items.map((item) => `
            <tr>
                <td><code>${escapeHtml(item.public_code)}</code></td>
                <td>
                    <span aria-hidden="true">${escapeHtml(item.icon)}</span>
                    ${escapeHtml(item.title)}
                    <div style="font-size:12px;color:#6b6b6b;">${escapeHtml(item.category)}</div>
                </td>
                <td>${formatDate(item.found_date)}</td>
                <td>${item.question_count}</td>
                <td>${statusBadge(item.status)}</td>
                <td>${item.pickup_code
                        ? `<code>${escapeHtml(item.pickup_code)}</code>
                           <div style="font-size:11.5px;color:#6b6b6b;">ver quem retirou na aba Reivindicações</div>`
                        : '—'}</td>
                <td>
                    ${item.status === 'available'
                        ? `<button type="button" class="btn btn--ghost btn--sm"
                                   data-archive="${escapeHtml(item.public_code)}">Arquivar</button>`
                        : ''}
                </td>
            </tr>
        `).join('');

        itemsBody.querySelectorAll('[data-archive]').forEach((button) => {
            button.addEventListener('click', async () => {
                const code = button.dataset.archive;
                if (!confirm(`Arquivar o item ${code}? Ele sairá da vitrine pública.`)) return;
                try {
                    await api.adminArchiveItem(code);
                    showAlert(alertBox, `Item ${code} arquivado.`, 'success');
                    await Promise.all([loadItems(), loadStats()]);
                } catch (error) {
                    showAlert(alertBox, error.message);
                }
            });
        });
    } catch (error) {
        itemsBody.innerHTML = '';
        showAlert(alertBox, error.message);
    }
}

/* -------------------------------------------------------------------------- */
/* Formulário de cadastro                                                      */
/* -------------------------------------------------------------------------- */

let attributeIndex = 0;

/** Adiciona um bloco de característica ao formulário de cadastro. */
function addAttributeRow(prefill = {}) {
    const index = attributeIndex++;
    const row = document.createElement('div');
    row.className = 'attribute-row';
    row.dataset.attribute = String(index);
    row.innerHTML = `
        <button type="button" class="attribute-row__remove" data-remove>remover</button>

        <div class="form-field">
            <label for="q-${index}">Pergunta exibida ao usuário</label>
            <input type="text" id="q-${index}" data-field="question" required
                   value="${escapeHtml(prefill.question || '')}"
                   placeholder="Ex.: Qual a cor predominante do objeto?">
        </div>

        <div class="form-row">
            <div class="form-field">
                <label for="a-${index}">Resposta correta (sigilosa)</label>
                <input type="text" id="a-${index}" data-field="expected_answer" required
                       placeholder="Ex.: roxo">
            </div>
            <div class="form-field">
                <label for="alt-${index}">Sinônimos aceitos</label>
                <input type="text" id="alt-${index}" data-field="alternatives"
                       placeholder="Separe por vírgula: lilás, violeta">
            </div>
        </div>

        <div class="form-row">
            <div class="form-field">
                <label for="t-${index}">Tipo do campo</label>
                <select id="t-${index}" data-field="field_type">
                    <option value="text">Texto curto</option>
                    <option value="textarea">Texto longo</option>
                    <option value="number">Número</option>
                    <option value="choice">Múltipla escolha</option>
                </select>
            </div>
            <div class="form-field">
                <label for="o-${index}">Opções (múltipla escolha)</label>
                <input type="text" id="o-${index}" data-field="options"
                       placeholder="Separe por vírgula">
            </div>
            <div class="form-field">
                <label for="w-${index}">Peso (1–10)</label>
                <input type="number" id="w-${index}" data-field="weight"
                       min="1" max="10" value="${prefill.weight || 2}">
            </div>
        </div>

        <label class="checkbox">
            <input type="checkbox" data-field="is_critical">
            Característica crítica — errar esta reprova a reivindicação inteira
        </label>
    `;

    row.querySelector('[data-remove]').addEventListener('click', () => {
        if (attributesEl.children.length > 1) row.remove();
        else showAlert(alertBox, 'O item precisa de pelo menos uma característica.', 'warning');
    });

    attributesEl.appendChild(row);
}

/** Lê os blocos de característica e monta o payload esperado pela API. */
function collectAttributes() {
    return [...attributesEl.querySelectorAll('[data-attribute]')].map((row) => {
        const value = (field) => row.querySelector(`[data-field="${field}"]`).value.trim();
        const splitList = (raw) =>
            raw.split(',').map((part) => part.trim()).filter(Boolean);

        const fieldType = value('field_type');
        const options = splitList(value('options'));

        return {
            question: value('question'),
            expected_answer: value('expected_answer'),
            field_type: fieldType,
            options: fieldType === 'choice' && options.length ? options : null,
            alternatives: splitList(value('alternatives')),
            weight: Number(value('weight')) || 1,
            is_critical: row.querySelector('[data-field="is_critical"]').checked,
        };
    });
}

itemForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearAlert(alertBox);

    const attributes = collectAttributes();
    if (attributes.some((attribute) => !attribute.question || !attribute.expected_answer)) {
        showAlert(alertBox, 'Preencha a pergunta e a resposta de todas as características.', 'warning');
        return;
    }

    const payload = {
        title: document.getElementById('item-title').value.trim(),
        category: document.getElementById('item-category').value.trim(),
        icon: document.getElementById('item-icon').value.trim() || '📦',
        found_date: document.getElementById('item-date').value,
        found_location: document.getElementById('item-location').value.trim() || null,
        internal_notes: document.getElementById('item-notes').value.trim() || null,
        attributes,
    };

    const button = event.target.querySelector('button[type="submit"]');
    const reset = setLoading(button, 'Cadastrando…');

    try {
        const created = await api.adminCreateItem(payload);
        showAlert(alertBox, created.message, 'success');
        itemForm.reset();
        attributesEl.innerHTML = '';
        addAttributeRow();
        document.getElementById('item-icon').value = '📦';
        await Promise.all([loadItems(), loadStats()]);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        showAlert(alertBox, error.message);
    } finally {
        reset();
    }
});

document.getElementById('add-attribute').addEventListener('click', () => addAttributeRow());

/* -------------------------------------------------------------------------- */
/* Reivindicações                                                              */
/* -------------------------------------------------------------------------- */

/** Barra de score colorida por faixa (reprovado / análise / aprovado). */
function scoreBar(score) {
    const percent = Math.round(score * 100);
    const variant = score >= 0.75 ? '' : score >= 0.55 ? 'score-bar__fill--mid' : 'score-bar__fill--low';
    return `
        <div style="display:flex;align-items:center;gap:10px;">
            <div class="score-bar" style="flex:1;">
                <div class="score-bar__fill ${variant}" style="width:${percent}%;"></div>
            </div>
            <strong style="font-size:13px;">${percent}%</strong>
        </div>
    `;
}

function claimCard(claim) {
    const details = claim.breakdown.map((entry) => `
        <li>
            <span>
                ${entry.matched ? '✅' : '❌'}
                ${escapeHtml(entry.question)}
                <em style="color:#6b6b6b;">— respondeu: "${escapeHtml(entry.given || '(vazio)')}"</em>
                ${entry.is_critical ? '<span class="badge badge--critical">crítica</span>' : ''}
            </span>
            <span><strong>${Math.round(entry.score * 100)}%</strong> · peso ${entry.weight}</span>
        </li>
    `).join('');

    const actions = claim.status === 'pending_review'
        ? `<div style="display:flex;gap:10px;margin-top:14px;">
               <button type="button" class="btn btn--green btn--sm" data-approve="${claim.id}">
                   Aprovar e emitir código
               </button>
               <button type="button" class="btn btn--danger btn--sm" data-reject="${claim.id}">
                   Recusar
               </button>
           </div>`
        : '';

    return `
        <div class="attribute-row">
            <div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;">
                <div>
                    <strong>${escapeHtml(claim.item_title)}</strong>
                    <code style="margin-left:8px;">${escapeHtml(claim.item_code)}</code>
                    <div style="font-size:13px;color:#6b6b6b;">
                        ${escapeHtml(claim.user_name)} · ${escapeHtml(claim.user_email)}
                        · ${formatDateTime(claim.created_at)}
                    </div>
                </div>
                <div style="text-align:right;">
                    ${statusBadge(claim.status)}
                    ${claim.pickup_code
                        ? `<div style="margin-top:6px;"><code>${escapeHtml(claim.pickup_code)}</code></div>`
                        : ''}
                </div>
            </div>

            <div style="margin-top:12px;max-width:340px;">${scoreBar(claim.score)}</div>

            <div class="breakdown"><ul>${details}</ul></div>
            ${actions}
        </div>
    `;
}

async function loadClaims() {
    try {
        const claims = await api.adminClaims({ status: statusFilter.value });

        if (!claims.length) {
            claimsList.innerHTML =
                '<p style="color:#6b6b6b;">Nenhuma reivindicação para exibir.</p>';
            return;
        }

        claimsList.innerHTML = claims.map(claimCard).join('');

        const decide = async (id, approve) => {
            try {
                const result = await api.adminReviewClaim(id, approve);
                showAlert(alertBox, result.message, approve ? 'success' : 'warning');
                await Promise.all([loadClaims(), loadItems(), loadStats()]);
            } catch (error) {
                showAlert(alertBox, error.message);
            }
        };

        claimsList.querySelectorAll('[data-approve]').forEach((button) =>
            button.addEventListener('click', () => decide(Number(button.dataset.approve), true)));
        claimsList.querySelectorAll('[data-reject]').forEach((button) =>
            button.addEventListener('click', () => decide(Number(button.dataset.reject), false)));
    } catch (error) {
        claimsList.innerHTML = '';
        showAlert(alertBox, error.message);
    }
}

statusFilter.addEventListener('change', loadClaims);

/* -------------------------------------------------------------------------- */
/* Relatórios (sp_relatorio_categorias / sp_relatorio_locais)                  */
/* -------------------------------------------------------------------------- */

async function loadReports() {
    try {
        const [categorias, locais] = await Promise.all([
            api.reportCategories(), api.reportLocations(10),
        ]);

        reportCategoriesBody.innerHTML = categorias.length
            ? categorias.map((row) => `
                <tr>
                    <td>${escapeHtml(row.category)}</td>
                    <td>${row.total_itens}</td>
                    <td>${row.total_devolvidos}</td>
                    <td>${row.taxa_recuperacao_pct}%</td>
                    <td>${row.total_tentativas}</td>
                    <td>${row.score_medio_aprovados_pct !== null ? row.score_medio_aprovados_pct + '%' : '—'}</td>
                </tr>
            `).join('')
            : '<tr><td colspan="6">Nenhum item cadastrado ainda.</td></tr>';

        reportLocationsBody.innerHTML = locais.length
            ? locais.map((row) => `
                <tr>
                    <td>${escapeHtml(row.local)}</td>
                    <td>${row.total_itens}</td>
                    <td>${row.total_devolvidos}</td>
                    <td>${row.taxa_recuperacao_pct}%</td>
                </tr>
            `).join('')
            : '<tr><td colspan="4">Nenhum item cadastrado ainda.</td></tr>';
    } catch (error) {
        showAlert(alertBox, error.message);
    }
}

/* -------------------------------------------------------------------------- */
/* Boot                                                                        */
/* -------------------------------------------------------------------------- */

renderChrome('admin');

if (!session.isAuthenticated) {
    session.requireAuth();
} else if (!session.isAdmin) {
    document.querySelector('.page .container').innerHTML = `
        <div class="empty-state">
            <div class="empty-state__icon" aria-hidden="true">🔒</div>
            <h3>Acesso restrito</h3>
            <p>Esta área é exclusiva para administradores.</p>
            <p style="margin-top:16px;"><a class="btn" href="index.html">Voltar ao início</a></p>
        </div>
    `;
} else {
    document.getElementById('item-date').valueAsDate = new Date();
    addAttributeRow();
    loadStats();
    loadItems();
    loadClaims();
    loadReports();
}
