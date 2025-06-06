import {t} from 'sentry/locale';

export const MODULE_TITLE = t('Outbound API Requests');
export const FRONTEND_MODULE_TITLE = t('Network Requests');
export const MOBILE_MODULE_TITLE = t('Network Requests');
export const DATA_TYPE = t('Request');
export const DATA_TYPE_PLURAL = t('Requests');
export const BASE_URL = 'http';

export const NULL_DOMAIN_DESCRIPTION = t('Unknown Domain');

export const SPAN_ID_DISPLAY_LENGTH = 16;

export const FIELD_ALIASES = {
  'http_response_rate(3)': '3XX',
  'http_response_rate(4)': '4XX',
  'http_response_rate(5)': '5XX',
};

export const BASE_FILTERS = {
  'span.op': 'http.client',
};

export const MODULE_DOC_LINK =
  'https://docs.sentry.io/product/insights/backend/requests/';

export const MODULE_FEATURES = ['insights-initial-modules'];
