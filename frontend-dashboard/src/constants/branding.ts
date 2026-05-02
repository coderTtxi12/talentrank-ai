/**
 * UI copy: recruiter dashboard for candidate screening (Grupo Sazón, delivery hiring).
 * Keep in sync with `index.html` title (`APP_HTML_TITLE`).
 *
 * @see backend/docs/FDE_Technical_Assignment.md
 */
export const APP_NAME = 'Orbio';

/** Browser tab — duplicate in `index.html` */
export const APP_HTML_TITLE = `${APP_NAME} · Screening candidatos`;

export const NAV_CONTEXT_LINE = 'Grupo Sazón · Screening repartidores';

export const NAV_HOME = 'Inicio';
export const NAV_CANDIDATES = 'Candidatos';
export const NAV_NEW_CANDIDATE = 'Nuevo candidato';

export const FILTER_BY_COUNTRY = 'Filtrar por país';
export const FILTER_BY_STATUS = 'Filtrar por estado';
export const CLEAR_FILTERS = 'Quitar filtros';

export const DASH_TITLE = 'Panel';
export const DASH_SUBTITLE =
  'Resumen del funnel de screening de candidatos (reparto)';
export const DASH_BTN_NEW = '+ Nuevo candidato';
export const DASH_STAT_TOTAL = 'Total candidatos';
export const DASH_STAT_RISK = 'Puntuación de riesgo media';
export const DASH_CHART_STATUS = 'Candidatos por estado';
export const DASH_CHART_COUNTRY = 'Candidatos por país';
export const DASH_RECENT_TITLE = 'Candidatos recientes';
export const DASH_RECENT_SUBTITLE = 'Últimos registros en el funnel';
export const DASH_EMPTY = 'Aún no hay candidatos';
export const DASH_VIEW_ALL = 'Ver todos los candidatos →';
export const DASH_RECENT_LOAD_MORE = 'Cargar más (WebSocket)';
export const SIDEBAR_CANDIDATES_TOTAL = (total: number) =>
  `${total.toLocaleString('es-ES')} en total`;
export const LIST_TITLE = 'Candidatos';
export const LIST_SUBTITLE =
  'Gestiona y revisa el screening en España y México';
export const LIST_BTN_NEW = '+ Nuevo candidato';
export const LIST_SHOWING = (shown: number, total: number) =>
  `Mostrando ${shown} de ${total} candidatos`;
export const LIST_FILTERS_ACTIVE = 'Filtros activos';

export const FILTERS_LABEL_COUNTRY = 'País';
export const FILTERS_ALL_COUNTRIES = 'Todos los países';
export const FILTERS_LABEL_STATUS = 'Estado';
export const FILTERS_ALL_STATUSES = 'Todos los estados';
export const FILTERS_CLEAR = 'Limpiar filtros';

export const CREATE_TITLE = 'Registrar candidato';
export const CREATE_SUBTITLE =
  'Completa el formulario para dar de alta un candidato en el funnel';
export const CREATE_BACK = '← Volver a candidatos';
export const CREATE_SUCCESS = 'Candidato registrado correctamente.';
export const CREATE_ERROR_FALLBACK = 'No se pudo registrar el candidato';

export const DETAIL_TITLE = 'Detalle del candidato';
export const DETAIL_BACK = '← Volver a candidatos';
export const DETAIL_NAV_SHORT = 'Volver a candidatos';
export const DETAIL_ERROR_LOAD = 'Error al cargar el candidato';
export const DETAIL_NOT_FOUND = 'Candidato no encontrado';
export const DETAIL_NOT_FOUND_DESC =
  'No encontramos un candidato con ese identificador.';
export const DETAIL_CARD_INFO = 'Datos del candidato';
export const DETAIL_CARD_HISTORY = 'Historial de estado';
export const DETAIL_BTN_CHANGE_STATUS = 'Cambiar estado';

export const FORM_CARD_COUNTRY_TITLE = 'País';
export const FORM_CARD_COUNTRY_SUB = 'Selecciona el país del candidato';
export const FORM_CARD_PERSON_TITLE = 'Datos del candidato';
export const FORM_CARD_PERSON_SUB = 'Nombre e identificación';
export const FORM_CARD_AMOUNTS_TITLE = 'Importes declarados';
export const FORM_CARD_AMOUNTS_SUB = 'Montos informados en la solicitud';
export const FORM_BTN_RESET = 'Restablecer';
export const FORM_BTN_SUBMIT = 'Registrar candidato';
export const FORM_BTN_SUBMIT_LOADING = 'Guardando…';

export const TABLE_EMPTY = 'No hay candidatos';
export const TABLE_EMPTY_HINT = 'Prueba a ajustar los filtros';
export const TABLE_COL_COUNTRY = 'País';
export const TABLE_COL_NAME = 'Candidato';
export const TABLE_COL_DOC = 'Documento';
export const TABLE_COL_AMOUNT = 'Importe';
export const TABLE_COL_STATUS = 'Estado';
export const TABLE_COL_RISK = 'Riesgo';
export const TABLE_COL_DATE = 'Fecha';
export const TABLE_TITLE_REVIEW = 'Requiere revisión';

export const INFO_STATUS_LABEL = 'Estado actual';
export const INFO_RISK_LABEL = 'Puntuación de riesgo';
export const INFO_REVIEW_BANNER =
  'Este candidato requiere revisión manual';
export const INFO_SECTION_APPLICANT = 'Datos del candidato';
export const INFO_SECTION_AMOUNTS = 'Importes declarados';

export const MODAL_STATUS_TITLE = 'Cambiar estado del candidato';
export const MODAL_CURRENT_STATUS = 'Estado actual';
export const MODAL_NEW_STATUS = 'Nuevo estado';
export const MODAL_NEW_STATUS_PH = 'Selecciona un estado';
export const MODAL_REASON_LABEL = 'Motivo (opcional)';
export const MODAL_REASON_PH = 'Motivo del cambio de estado';
export const MODAL_SELECT_ERROR = 'Selecciona un estado';
export const MODAL_BTN_CANCEL = 'Cancelar';
export const MODAL_BTN_CONFIRM = 'Confirmar cambio';
export const MODAL_NO_TRANSITIONS_PREFIX =
  'No hay transiciones disponibles desde';
export const MODAL_BTN_CLOSE = 'Cerrar';

export const RT_CONNECTED = 'En vivo';
export const RT_OFFLINE = 'Desconectado';

export const TOAST_NEW_CANDIDATE = (id: string) => `Nuevo candidato: ${id}`;
export const TOAST_STATUS_LINE = (shortId: string, label: string) =>
  `Candidato ${shortId}… → ${label}`;

export const ERR_FETCH_LIST = 'No se pudieron cargar los candidatos';
export const ERR_FETCH_ONE = 'No se pudo cargar el candidato';
export const ERR_CREATE = 'No se pudo registrar el candidato';
export const ERR_UPDATE_STATUS = 'No se pudo actualizar el estado';
export const ERR_HISTORY = 'No se pudo cargar el historial';
export const ERR_STATS = 'No se pudieron cargar las estadísticas';
