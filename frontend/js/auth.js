/**
 * Tela de login e cadastro.
 *
 * Após autenticar, respeita o parâmetro `?next=` para devolver o usuário à
 * página que ele tentava acessar (tipicamente o questionário de um item).
 */

import { api, session } from './api.js';
import { clearAlert, renderChrome, setLoading, showAlert } from './ui.js';

const tabs = document.querySelectorAll('[data-tab]');
const loginForm = document.getElementById('form-login');
const registerForm = document.getElementById('form-register');
const alertBox = document.querySelector('[data-alert]');
const title = document.getElementById('auth-title');
const subtitle = document.getElementById('auth-subtitle');

/** Destino pós-login: `?next=` quando presente, senão o dashboard. */
function redirectTarget() {
    const next = new URLSearchParams(location.search).get('next');
    // Só aceita caminhos internos — evita open redirect para domínio externo.
    if (next && next.startsWith('/') && !next.startsWith('//')) return next;
    if (next && /^[\w./?=&%-]+$/.test(next) && !next.includes(':')) return next;
    return 'index.html';
}

function activateTab(name) {
    tabs.forEach((tab) => tab.classList.toggle('is-active', tab.dataset.tab === name));
    loginForm.classList.toggle('hidden', name !== 'login');
    registerForm.classList.toggle('hidden', name !== 'register');
    title.textContent = name === 'login' ? 'Acessar o portal' : 'Criar sua conta';
    subtitle.textContent = name === 'login'
        ? 'Identifique-se para reivindicar um item encontrado.'
        : 'O cadastro vincula cada reivindicação a uma identidade real.';
    clearAlert(alertBox);
}

tabs.forEach((tab) => tab.addEventListener('click', () => activateTab(tab.dataset.tab)));

/** Handler comum às duas operações: chama a API, salva a sessão e redireciona. */
async function authenticate(event, operation, buildPayload) {
    event.preventDefault();
    clearAlert(alertBox);

    const button = event.target.querySelector('button[type="submit"]');
    const reset = setLoading(button, 'Processando…');

    try {
        const result = await operation(buildPayload());
        session.save(result.access_token, result.user);
        // Administrador cai direto no painel; aluno segue o fluxo original.
        location.href = result.user.role === 'admin' ? 'admin.html' : redirectTarget();
    } catch (error) {
        showAlert(alertBox, error.message);
        reset();
    }
}

loginForm.addEventListener('submit', (event) =>
    authenticate(event, api.login, () => ({
        email: document.getElementById('login-email').value.trim(),
        password: document.getElementById('login-password').value,
    })));

registerForm.addEventListener('submit', (event) =>
    authenticate(event, api.register, () => ({
        name: document.getElementById('register-name').value.trim(),
        email: document.getElementById('register-email').value.trim(),
        password: document.getElementById('register-password').value,
    })));

// Quem já está logado não precisa ver esta tela.
if (session.isAuthenticated) {
    location.replace(redirectTarget());
} else {
    renderChrome('login');
}
