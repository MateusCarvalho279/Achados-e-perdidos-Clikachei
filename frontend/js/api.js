/**
 * Camada de acesso à API REST + gestão da sessão no navegador.
 *
 * Tudo que fala com o backend passa por aqui. Assim o token é anexado em um
 * único lugar e o tratamento de 401 (sessão expirada) é uniforme.
 */

const API_BASE = '/api';
const TOKEN_KEY = 'lf_token';
const USER_KEY = 'lf_user';

/** Erro de API com o status HTTP preservado, para o chamador decidir a reação. */
export class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
    }
}

/* -------------------------------------------------------------------------- */
/* Sessão                                                                      */
/* -------------------------------------------------------------------------- */

export const session = {
    get token() {
        return localStorage.getItem(TOKEN_KEY);
    },

    get user() {
        try {
            return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
        } catch {
            return null;
        }
    },

    get isAuthenticated() {
        return Boolean(this.token);
    },

    get isAdmin() {
        return this.user?.role === 'admin';
    },

    save(token, user) {
        localStorage.setItem(TOKEN_KEY, token);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
    },

    clear() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    },

    /**
     * Exige login para acessar a página atual.
     * Guarda a URL de origem para retornar a ela após autenticar.
     */
    requireAuth() {
        if (this.isAuthenticated) return true;
        const next = encodeURIComponent(location.pathname + location.search);
        location.href = `login.html?next=${next}`;
        return false;
    },
};

/* -------------------------------------------------------------------------- */
/* Requisições                                                                 */
/* -------------------------------------------------------------------------- */

/**
 * Executa uma requisição autenticada e desembrulha a resposta JSON.
 *
 * @param {string} path   Caminho relativo a /api (ex.: '/items').
 * @param {object} options  { method, body, auth }
 * @returns {Promise<any>}
 * @throws {ApiError}
 */
async function request(path, { method = 'GET', body = null, auth = true } = {}) {
    const headers = { Accept: 'application/json' };

    if (body !== null) headers['Content-Type'] = 'application/json';
    if (auth && session.token) headers.Authorization = `Bearer ${session.token}`;

    let response;
    try {
        response = await fetch(`${API_BASE}${path}`, {
            method,
            headers,
            body: body === null ? null : JSON.stringify(body),
        });
    } catch {
        throw new ApiError('Não foi possível falar com o servidor.', 0);
    }

    if (response.status === 204) return null;

    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
        // Sessão expirada: limpa o estado local para não deixar o usuário
        // preso em um "logado" que o backend já não reconhece.
        if (response.status === 401 && session.isAuthenticated) session.clear();
        throw new ApiError(normalizeDetail(payload) || 'Erro inesperado.', response.status);
    }

    return payload;
}

/** O backend Flask devolve `detail` sempre como string. */
function normalizeDetail(payload) {
    const detail = payload?.detail;
    return typeof detail === 'string' ? detail : null;
}

/** Monta a query string a partir de um objeto, ignorando valores vazios. */
function buildQuery(params) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params || {})) {
        if (value !== null && value !== undefined && value !== '') query.set(key, value);
    }
    const text = query.toString();
    return text ? `?${text}` : '';
}

/* -------------------------------------------------------------------------- */
/* Endpoints                                                                   */
/* -------------------------------------------------------------------------- */

export const api = {
    /* Autenticação */
    register: (data) => request('/auth/register', { method: 'POST', body: data, auth: false }),
    login: (data) => request('/auth/login', { method: 'POST', body: data, auth: false }),
    me: () => request('/auth/me'),

    /* Itens — busca avançada (filtros + ordenação via sp_buscar_itens) */
    listItems: (filters = {}) => request(`/items${buildQuery(filters)}`, { auth: false }),
    getItem: (code) => request(`/items/${encodeURIComponent(code)}`, { auth: false }),
    getQuestionnaire: (code) => request(`/items/${encodeURIComponent(code)}/questionnaire`),

    /* Reivindicações */
    submitClaim: (itemCode, answers) =>
        request('/claims', { method: 'POST', body: { item_code: itemCode, answers } }),
    /* Histórico do usuário — filtro + ordenação via sp_historico_usuario */
    myClaims: (filters = {}) => request(`/claims/mine${buildQuery(filters)}`),

    /* Administração */
    adminStats: () => request('/admin/stats'),
    adminItems: () => request('/admin/items'),
    adminCreateItem: (data) => request('/admin/items', { method: 'POST', body: data }),
    adminArchiveItem: (code) =>
        request(`/admin/items/${encodeURIComponent(code)}`, { method: 'DELETE' }),
    adminItemAttributes: (code) =>
        request(`/admin/items/${encodeURIComponent(code)}/attributes`),
    /* Auditoria de reivindicações — JOIN via sp_listar_reivindicacoes */
    adminClaims: (filters = {}) => request(`/admin/claims${buildQuery(filters)}`),
    adminReviewClaim: (id, approve) =>
        request(`/admin/claims/${id}/review`, { method: 'POST', body: { approve } }),

    /* Relatórios gerenciais */
    reportCategories: () => request('/admin/reports/categories'),
    reportLocations: (limite = 10) => request(`/admin/reports/locations${buildQuery({ limite })}`),
};
