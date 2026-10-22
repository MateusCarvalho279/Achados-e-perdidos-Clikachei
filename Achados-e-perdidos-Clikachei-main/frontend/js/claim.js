/**
 * Tela do questionário de reivindicação.
 *
 * Fluxo: exige login → busca as perguntas do item → monta o formulário dinâmico
 * a partir do `field_type` de cada característica → envia as respostas → exibe
 * o veredito (com o código de retirada, se aprovado).
 */

import { api, session } from './api.js';
import {
    clearAlert, escapeHtml, formatDate, icons, renderChrome, setLoading, showAlert,
} from './ui.js';

const itemCode = new URLSearchParams(location.search).get('item');

const headerEl = document.getElementById('item-header');
const questionnaireCard = document.getElementById('questionnaire-card');
const questionsEl = document.getElementById('questions');
const resultCard = document.getElementById('result-card');
const loadingEl = document.getElementById('loading-state');
const form = document.getElementById('claim-form');
const alertBox = document.querySelector('[data-alert]');

/* -------------------------------------------------------------------------- */
/* Renderização                                                                */
/* -------------------------------------------------------------------------- */

function renderHeader(item, attemptsLeft) {
    headerEl.innerHTML = `
        <div class="claim-header__icon" aria-hidden="true">${escapeHtml(item.icon)}</div>
        <div class="claim-header__info">
            <h1 style="font-size:20px;">${escapeHtml(item.title)}</h1>
            <div class="claim-header__meta">
                <span>${icons.hash}<code>${escapeHtml(item.public_code)}</code></span>
                <span>${icons.calendar}${formatDate(item.found_date)}</span>
                ${item.found_location
                    ? `<span>${icons.pin}${escapeHtml(item.found_location)}</span>`
                    : ''}
            </div>
        </div>
        <div class="attempts-pill">
            <strong>${attemptsLeft}</strong>
            tentativa(s) restante(s)
        </div>
    `;
    headerEl.classList.remove('hidden');
}

/**
 * Constrói o campo de entrada adequado ao tipo da característica.
 * O `name` do campo é o id do atributo — é assim que o backend correlaciona
 * resposta e gabarito sem nunca expor a resposta esperada.
 */
function questionField(question, index) {
    const name = `attr-${question.id}`;
    const placeholder = escapeHtml(question.placeholder || 'Descreva com detalhes…');
    let input;

    switch (question.field_type) {
        case 'textarea':
            input = `<textarea id="${name}" name="${name}" placeholder="${placeholder}" required></textarea>`;
            break;

        case 'number':
            input = `<input type="number" step="any" id="${name}" name="${name}"
                            placeholder="${placeholder}" required>`;
            break;

        case 'choice': {
            const options = (question.options || [])
                .map((option) => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`)
                .join('');
            input = `<select id="${name}" name="${name}" required>
                        <option value="">Selecione…</option>${options}
                     </select>`;
            break;
        }

        default:
            input = `<input type="text" id="${name}" name="${name}"
                            placeholder="${placeholder}" required>`;
    }

    return `
        <div class="question">
            <label class="question__label" for="${name}">
                <span class="question__number" aria-hidden="true">${index + 1}</span>
                <span>
                    ${escapeHtml(question.question)}
                    ${question.is_critical
                        ? '<span class="badge badge--critical" style="margin-left:8px;">Obrigatória</span>'
                        : ''}
                </span>
            </label>
            ${input}
        </div>
    `;
}

/** Tela final: aprovado (com código), em análise ou recusado. */
function renderResult(result) {
    questionnaireCard.classList.add('hidden');
    headerEl.classList.add('hidden');

    const presentation = {
        approved: { icon: '✅', title: 'Item liberado para retirada!' },
        pending_review: { icon: '🔎', title: 'Pedido em análise' },
        rejected: { icon: '⚠️', title: 'Não foi possível confirmar' },
    }[result.status] || { icon: 'ℹ️', title: 'Resultado' };

    const codeBlock = result.pickup_code
        ? `<div class="pickup-code">
               <div class="pickup-code__label">Código de retirada</div>
               <div class="pickup-code__value">${escapeHtml(result.pickup_code)}</div>
               <div class="pickup-code__note">
                   Válido apenas com documento com foto · Secretaria, 7h às 18h
               </div>
           </div>`
        : '';

    const canRetry = result.status === 'rejected' && result.attempts_left > 0;

    resultCard.innerHTML = `
        <div class="result__icon" aria-hidden="true">${presentation.icon}</div>
        <h2 class="result__title">${presentation.title}</h2>
        <p class="result__message">${escapeHtml(result.message)}</p>
        ${codeBlock}
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
            ${canRetry
                ? '<button type="button" class="btn" id="retry">Tentar novamente</button>'
                : ''}
            <a class="btn btn--ghost" href="meus-pedidos.html">Meus pedidos</a>
            <a class="btn btn--ghost" href="index.html">Voltar para a lista</a>
        </div>
    `;
    resultCard.classList.remove('hidden');

    document.getElementById('retry')?.addEventListener('click', () => location.reload());
}

/* -------------------------------------------------------------------------- */
/* Carregamento e envio                                                        */
/* -------------------------------------------------------------------------- */

async function loadQuestionnaire() {
    try {
        const data = await api.getQuestionnaire(itemCode);
        renderHeader(data.item, data.attempts_left);
        questionsEl.innerHTML = data.questions.map(questionField).join('');
        questionnaireCard.classList.remove('hidden');
    } catch (error) {
        // 401 já limpou a sessão em api.js; mandamos o usuário logar de novo.
        if (error.status === 401) {
            session.requireAuth();
            return;
        }
        showAlert(alertBox, error.message, error.status === 409 ? 'warning' : 'error');
    } finally {
        loadingEl.classList.add('hidden');
    }
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearAlert(alertBox);

    if (!document.getElementById('declaration').checked) {
        showAlert(alertBox, 'É necessário confirmar a declaração de propriedade.', 'warning');
        return;
    }

    // Coleta as respostas no formato { id_do_atributo: texto }.
    const answers = {};
    let incomplete = false;

    questionsEl.querySelectorAll('[name^="attr-"]').forEach((field) => {
        const value = field.value.trim();
        if (!value) incomplete = true;
        answers[field.name.replace('attr-', '')] = value;
    });

    if (incomplete) {
        showAlert(alertBox, 'Responda todas as perguntas antes de enviar.', 'warning');
        return;
    }

    const button = document.getElementById('submit-claim');
    const reset = setLoading(button, 'Validando respostas…');

    try {
        renderResult(await api.submitClaim(itemCode, answers));
    } catch (error) {
        showAlert(alertBox, error.message, 'warning');
        reset();
    }
});

/* -------------------------------------------------------------------------- */
/* Boot                                                                        */
/* -------------------------------------------------------------------------- */

renderChrome('home');

if (!itemCode) {
    loadingEl.classList.add('hidden');
    showAlert(alertBox, 'Nenhum item foi informado na URL.');
} else if (session.requireAuth()) {
    loadQuestionnaire();
}
