import http from 'k6/http';
import { check, group, sleep, fail } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';

const TEST_ENV = __ENV.K6_ENV || 'local';
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const FILMS_URL = `${BASE_URL}/api/films/`;
const AUTHORS_URL = `${BASE_URL}/api/authors/`;
const SPECTATOR_ME_URL = `${BASE_URL}/api/spectators/me/`;
const LOGIN_URL = __ENV.LOGIN_URL || `${BASE_URL}/api/login/`;
const TIMEOUT = __ENV.K6_TIMEOUT || '30s';
const PAGE_SIZE = Number(__ENV.K6_PAGE_SIZE || 24);
const SLEEP_MIN = Number(__ENV.K6_SLEEP_MIN || 0.4);
const SLEEP_MAX = Number(__ENV.K6_SLEEP_MAX || 1.8);

const START_RATE = Number(__ENV.K6_START_RATE || 8);
const PEAK_RATE = Number(__ENV.K6_PEAK_RATE || 50);
const RECOVER_RATE = Number(__ENV.K6_RECOVER_RATE || 15);
const MAX_VUS = Number(__ENV.K6_MAX_VUS || 120);
const AUTH_RATE = Number(__ENV.K6_AUTH_RATE || 25);
const AUTH_VUS = Number(__ENV.K6_AUTH_VUS || 50);
const SOAK_VUS = Number(__ENV.K6_SOAK_VUS || 12);

const catalogueDuration = new Trend('catalogue_duration', true);
const authDuration = new Trend('auth_duration', true);
const payloadErrors = new Rate('payload_errors');
const serverErrors = new Counter('server_errors');

export const options = {
  scenarios: {
    warmup: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '1m', target: 10 },
        { duration: '1m', target: 20 },
      ],
      gracefulStop: '15s',
      exec: 'catalogueScenario',
    },
    ramp: {
      executor: 'ramping-arrival-rate',
      startRate: START_RATE,
      preAllocatedVUs: MAX_VUS,
      maxVUs: MAX_VUS,
      timeUnit: '1s',
      stages: [
        { target: PEAK_RATE, duration: __ENV.K6_RAMP_UP || '3m' },
        { target: PEAK_RATE, duration: __ENV.K6_PEAK_HOLD || '4m' },
        { target: RECOVER_RATE, duration: __ENV.K6_RAMP_DOWN || '2m' },
      ],
      gracefulStop: '30s',
      exec: 'mixedScenario',
      startTime: '2m',
    },
    auth_spike: {
      executor: 'constant-arrival-rate',
      rate: AUTH_RATE,
      duration: __ENV.K6_AUTH_DURATION || '3m',
      timeUnit: '1s',
      preAllocatedVUs: AUTH_VUS,
      maxVUs: AUTH_VUS * 2,
      gracefulStop: '30s',
      exec: 'authScenario',
      startTime: '6m',
    },
    soak: {
      executor: 'constant-vus',
      vus: SOAK_VUS,
      duration: __ENV.K6_SOAK_DURATION || '10m',
      gracefulStop: '30s',
      exec: 'catalogueScenario',
      startTime: '9m',
    },
  },
  // Thresholds disabled for pure measurement - no failure if exceeded
  thresholds: {},
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  tags: {
    env: TEST_ENV,
  },
};

export function setup() {
  const authPayload =
    __ENV.K6_USER && __ENV.K6_PASS
      ? JSON.stringify({ username: __ENV.K6_USER, password: __ENV.K6_PASS })
      : null;

  const baseHeaders = { 'Content-Type': 'application/json' };
  let token = null;

  if (authPayload) {
    const res = http.post(LOGIN_URL, authPayload, {
      headers: baseHeaders,
      timeout: TIMEOUT,
      tags: { endpoint: 'auth_bootstrap', env: TEST_ENV },
    });

    const loginOk = check(res, { 
      'bootstrap login 200': (r) => r.status === 200,
      'bootstrap login has body': (r) => r.body && r.body.length > 0
    }, { type: 'auth' });
    
    if (loginOk && res.status === 200) {
      try {
        const jsonData = res.json();
        token = jsonData.access || null;
      } catch (e) {
        console.error('Failed to parse login response:', e);
      }
    } else {
      console.error('Login failed:', res.status, res.body);
    }
  }

  const filmIds = bootstrapIds(`${FILMS_URL}?page_size=${PAGE_SIZE}`, 'films_bootstrap');
  const authorIds = bootstrapIds(`${AUTHORS_URL}?page_size=${PAGE_SIZE}`, 'authors_bootstrap');

  return {
    token,
    authPayload,
    baseHeaders,
    filmIds,
    authorIds,
  };
}

export function catalogueScenario(data) {
  browseCatalogue(data);
  think();
}

export function mixedScenario(data) {
  browseCatalogue(data, true);

  if (data.token) {
    group('profile refresh', () => {
      const res = timedRequest(
        () => http.get(SPECTATOR_ME_URL, requestParams('spectator_me', authHeaders(data.token))),
        authDuration,
        { step: 'me' }
      );

      check(res, { 'me 200': (r) => r.status === 200 }, { type: 'auth' });
    });
  }

  think();
}

export function authScenario(data) {
  if (!data.authPayload) {
    fail('Set K6_USER and K6_PASS to run the auth scenario.');
  }

  group('auth spike', () => {
    const loginRes = timedRequest(
      () => http.post(LOGIN_URL, data.authPayload, requestParams('auth_login', data.baseHeaders)),
      authDuration,
      { step: 'login' }
    );

    const loginOk = check(loginRes, {
      'login 200': (r) => r.status === 200,
      'login has token': (r) => !!r.json('access'),
    }, { type: 'auth' });

    if (!loginOk) {
      payloadErrors.add(1, { source: 'login' });
      return;
    }

    const token = loginRes.json('access');
    const profile = timedRequest(
      () => http.get(SPECTATOR_ME_URL, requestParams('auth_me', authHeaders(token))),
      authDuration,
      { step: 'me' }
    );

    check(profile, { 'profile 200': (r) => r.status === 200 }, { type: 'auth' });
  });

  think();
}

function browseCatalogue(data, includeDetail = false) {
  group('catalogue sweep', () => {
    const responses = http.batch([
      ['GET', `${FILMS_URL}?page_size=${PAGE_SIZE}&ordering=-release_date`, requestParams('films_list')],
      ['GET', `${AUTHORS_URL}?page_size=${PAGE_SIZE}`, requestParams('authors_list')],
    ]);

    const [filmsRes, authorsRes] = responses;
    recordCatalogue(filmsRes, 'list');
    recordCatalogue(authorsRes, 'list');

    const filmsOk = check(filmsRes, {
      'films list 200': (r) => r.status === 200,
      'films payload ok': (r) => hasResults(r),
    }, { type: 'catalogue' });

    const authorsOk = check(authorsRes, {
      'authors list 200': (r) => r.status === 200,
      'authors payload ok': (r) => hasResults(r),
    }, { type: 'catalogue' });

    if (!filmsOk || !authorsOk) {
      payloadErrors.add(1, { source: 'list' });
    }

    if (includeDetail) {
      const filmId = pick(data.filmIds);
      const authorId = pick(data.authorIds);

      if (filmId) {
        const film = timedRequest(
          () => http.get(`${FILMS_URL}${filmId}/`, requestParams('films_detail')),
          catalogueDuration,
          { kind: 'detail' }
        );
        check(film, { 'film detail 200': (r) => r.status === 200 }, { type: 'catalogue' });
      }

      if (authorId) {
        const author = timedRequest(
          () => http.get(`${AUTHORS_URL}${authorId}/`, requestParams('authors_detail')),
          catalogueDuration,
          { kind: 'detail' }
        );
        check(author, { 'author detail 200': (r) => r.status === 200 }, { type: 'catalogue' });
      }
    }
  });
}

function bootstrapIds(url, endpointTag) {
  const res = http.get(url, requestParams(endpointTag));
  recordCatalogue(res, 'list');

  if (res.status >= 500) {
    serverErrors.add(1, { endpoint: endpointTag });
  }

  if (!res.body || res.body.length === 0) {
    console.warn(`Bootstrap ${endpointTag}: empty response body`);
    return [];
  }

  if (!hasResults(res)) {
    console.warn(`Bootstrap ${endpointTag}: no results in response`);
    return [];
  }

  try {
    const items = res.json('results');
    return items.map((item) => item.id).filter(Boolean);
  } catch (e) {
    console.error(`Bootstrap ${endpointTag}: failed to parse JSON:`, e);
    return [];
  }
}

function timedRequest(fn, trend, tags) {
  const res = fn();
  trend.add(res.timings.duration, tags);
  if (res.status >= 500) {
    const label = res.request && res.request.url ? res.request.url : 'unknown';
    serverErrors.add(1, { endpoint: label });
  }
  return res;
}

function recordCatalogue(res, kind) {
  catalogueDuration.add(res.timings.duration, { kind });
  if (res.status >= 500) {
    const label = res.request && res.request.url ? res.request.url : 'catalogue';
    serverErrors.add(1, { endpoint: label });
  }
}

function hasResults(res) {
  try {
    const results = res.json('results');
    return Array.isArray(results) && results.length > 0;
  } catch (err) {
    return false;
  }
}

function requestParams(endpointTag, headers = {}) {
  return {
    headers,
    timeout: TIMEOUT,
    tags: { endpoint: endpointTag, env: TEST_ENV },
  };
}

function authHeaders(token) {
  return { Authorization: `Bearer ${token}` };
}

function pick(items = []) {
  if (!items.length) {
    return null;
  }
  return items[Math.floor(Math.random() * items.length)];
}

function think() {
  const delta = Math.random() * (SLEEP_MAX - SLEEP_MIN);
  sleep(SLEEP_MIN + delta);
}

export function handleSummary(data) {
  const summary = {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };

  if (__ENV.K6_SUMMARY_JSON) {
    // Write to the /scripts directory mounted by Docker
    summary['/scripts/summary.json'] = JSON.stringify(data, null, 2);
  }

  return summary;
}
