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
export const NAV_TOURNAMENTS = 'Torneos';
export const NAV_NEW_CANDIDATE = 'Nuevo candidato';

export const FILTER_BY_COUNTRY = 'Filtrar por país';
export const FILTER_BY_STATUS = 'Filtrar por estado';
export const CLEAR_FILTERS = 'Quitar filtros';

export const DASH_TITLE = 'Panel';
export const DASH_SUBTITLE =
  'Resumen del funnel de screening de candidatos (reparto)';
export const DASH_BTN_NEW = 'Run Listwise + Plackett–Luce';
export const DASH_BTN_SIMULATION = 'Run Simulation';
export const DASH_SIM_MODAL_TITLE = '¿Cargar cohorte simulada de screening?';
export const DASH_SIM_MODAL_BODY =
  'Se insertarán 10 candidatos sintéticos con conversación de screening completada.';
export const DASH_SIM_MODAL_CANCEL = 'Cancelar';
export const DASH_SIM_MODAL_CONFIRM = 'Sí, cargar simulación';
export const DASH_SIM_SUBMITTING = 'Insertando datos…';
export const DASH_SIM_SUCCESS = (batchId: string, n: number) =>
  `Simulación lista: ${n} candidatos (lote ${batchId}).`;
export const DASH_SIM_WARN_ALREADY_RAN =
  'Esta simulación ya se ejecutó en el servidor; no se pueden insertar más datos sintéticos.';
export const DASH_SIM_USED_HINT =
  'La simulación ya se ejecutó en este navegador. Para volver a cargar datos simulados, borra el almacenamiento local del sitio o usa otra ventana privada.';
export const DASH_RANK_MODAL_TITLE =
  '¿Confirmas ejecutar Listwise + Plackett–Luce en el batch actual?';
export const DASH_RANK_MODAL_BODY =
  'Se crearan torneos y subagentes clasificaran a los mejores candidatos. Plackett-Luce analizará los resultados de los subagentes y encontrará un patrón en la data, así eligiiendo a los top mejores postulantes.';
export const DASH_RANK_MODAL_CANCEL = 'Cancelar';
export const DASH_RANK_MODAL_CONFIRM = 'Sí, ejecutar';
export const DASH_RANK_SUBMITTING = 'Encolando…';
export const DASH_RANK_SUCCESS = (jobId: string) =>
  `Trabajo encolado. ID: ${jobId.slice(0, 8)}…`;
export const DASH_RANK_ERROR_GENERIC =
  'No se pudo encolar el trabajo. Revisa la red o los logs del API.';
export const DASH_STAT_TOTAL = 'Total candidatos';
export const DASH_STAT_LISTWISE_QUEUE = 'Listos para listwise';
export const DASH_STAT_POST_PL = 'Rankeados (Plackett–Luce)';
export const DASH_CHART_STATUS = 'Candidatos por estado';
export const DASH_CHART_COUNTRY = 'Candidatos por país';
export const DASH_RECENT_TITLE = 'Candidatos recientes';
export const DASH_RECENT_SUBTITLE = 'Últimos registros en el funnel';
export const DASH_EMPTY = 'Aún no hay candidatos';
export const DASH_VIEW_ALL = 'Ver todos los candidatos →';
export const DASH_RECENT_LOAD_MORE = 'Cargar más';
export const SIDEBAR_CANDIDATES_TOTAL = (total: number) =>
  `${total.toLocaleString('es-ES')} en total`;
export const LIST_TITLE = 'Candidatos';
export const LIST_SUBTITLE =
  'Gestiona y revisa el screening en España y México';
export const LIST_SHOWING = (shown: number, total: number) =>
  `Mostrando ${shown} de ${total} candidatos`;
export const LIST_FILTERS_ACTIVE = 'Filtros activos';

export const TOURNAMENTS_TITLE = 'Torneos de ranking';
export const TOURNAMENTS_SUBTITLE =
  'Por corrida: mini-torneos listwise y, si hubo fit, el ranking global Plackett–Luce.';
export const TOURNAMENTS_COL_CREATED = 'Fecha';
export const TOURNAMENTS_COL_RUN = 'Corrida';
export const TOURNAMENTS_RUN_META = (
  rubric: string,
  pool: number,
  status: string,
  nTournaments: number
) =>
  `Rúbrica: ${rubric} · Pool: ${pool} · Estado: ${status} · ${nTournaments} mini-torneo(s)`;
export const TOURNAMENTS_COL_TOURNAMENT = 'Torneo';
export const TOURNAMENTS_COL_K = 'En grupo';
export const TOURNAMENTS_COL_MODEL = 'Modelo';
export const TOURNAMENTS_COL_ORDER = 'Orden LLM';
export const TOURNAMENTS_COL_TRACE = 'Razonamiento (subagente)';
export const TOURNAMENTS_EMPTY = 'Aún no hay torneos en base de datos.';
export const TOURNAMENTS_ERROR =
  'No se pudieron cargar los torneos. Revisa la API o el proxy.';
export const TOURNAMENTS_PREV = 'Anterior';
export const TOURNAMENTS_NEXT = 'Siguiente';
export const TOURNAMENTS_PAGINATION = (from: number, to: number, total: number) =>
  `${from.toLocaleString('es-ES')}–${to.toLocaleString('es-ES')} de ${total.toLocaleString('es-ES')}`;
export const TOURNAMENTS_PAGINATION_RUNS = (from: number, to: number, totalRuns: number) =>
  `Corridas ${from.toLocaleString('es-ES')}–${to.toLocaleString('es-ES')} de ${totalRuns.toLocaleString('es-ES')}`;

export const TOURNAMENTS_PL_TITLE = 'Ranking global (Plackett–Luce)';
export const TOURNAMENTS_PL_EMPTY =
  'No hay resultados PL persistidos para esta corrida (sin contrastes en torneos o datos incompletos).';
export const TOURNAMENTS_PL_COL_RANK = '#';
export const TOURNAMENTS_PL_COL_CANDIDATE = 'Candidato';
export const TOURNAMENTS_PL_COL_UTILITY = 'Utilidad';
export const TOURNAMENTS_PL_COL_SEEN = 'Apariciones';

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
export const DETAIL_BTN_CONVERSATION = 'Ver conversación';
export const DETAIL_CONVERSATION_TITLE = 'Historial de conversación';
export const DETAIL_CONVERSATION_EMPTY =
  'No hay mensajes de screening guardados para este candidato.';
export const DETAIL_CONVERSATION_LOAD_MORE = 'Cargar más';
export const DETAIL_CONVERSATION_LOADING = 'Cargando mensajes…';
export const DETAIL_CONVERSATION_ROLE_USER = 'Candidato';
export const DETAIL_CONVERSATION_ROLE_ASSISTANT = 'Asistente';

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
export const TABLE_COL_DRIVERS_LICENSE = 'Licencia de conducir';
export const TABLE_COL_CITY_ZONE = 'Ciudad / zona';
export const TABLE_COL_AVAILABILITY = 'Disponibilidad';
export const TABLE_COL_PREFERRED_SCHEDULE = 'Horario preferido';
export const TABLE_COL_EXPERIENCE_YEARS = 'Años de experiencia';
export const TABLE_COL_PLATFORMS = 'Plataformas';
export const TABLE_COL_START_DATE = 'Fecha de inicio';
export const TABLE_COL_STATUS = 'Estado';
export const TABLE_COL_DATE = 'Fecha de alta';
export const TABLE_TITLE_REVIEW = 'Requiere revisión';

export const INFO_STATUS_LABEL = 'Estado actual';
export const INFO_RISK_LABEL = 'Puntuación de riesgo';
export const INFO_REVIEW_BANNER =
  'Este candidato requiere revisión manual';
export const INFO_SECTION_APPLICANT = 'Datos del candidato';
export const INFO_SECTION_POST_CONVERSATION_SUMMARY = 'Resumen post-conversación';
export const INFO_FULL_NAME = 'Nombre completo';
export const INFO_SECTION_TIMELINE = 'Cronología';
export const INFO_SECTION_BANKING = 'Información bancaria';
export const INFO_SECTION_RISK = 'Análisis de riesgo';
export const INFO_SECTION_SENTIMENT = 'Análisis de sentimientos';
export const INFO_SECTION_SENTIMENT_HINT =
  'Automático sobre la conversación de screening (IA)';
export const INFO_SENTIMENT_CLASSIFICATION = 'Clasificación de sentimiento';

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
export const ERR_CONVERSATION = 'No se pudo cargar la conversación';
export const ERR_STATS = 'No se pudieron cargar las estadísticas';
