'use client';
import { useEffect, useState, useRef, useCallback, useMemo, FormEvent } from 'react';
import dynamic from 'next/dynamic';
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Bell,
  ChartNoAxesCombined,
  ChevronRight,
  Flame,
  Layers,
  LayoutDashboard,
  LogOut,
  MapPinned,
  RefreshCw,
  Search,
  Send,
  Settings,
  Shield,
  ShieldCheck,
  Sparkles,
  Users,
  X,
  Database,
  ScanLine,
  Menu,
  Radio,
  FileCheck,
  Eye,
  EyeOff,
  Server,
} from 'lucide-react';
import {
  apiGet,
  apiPost,
  apiPut,
  loadWorkspace,
  fetchHealth,
  fetchProviderStatus,
  fetchEonetEvents,
  storeToken,
  getStoredToken,
  ApiError,
  ThermalEvent,
  User,
  ModelStatus,
  Alert,
  FirmsStatus,
  FirmsSyncResponse,
  AnalyticsResponse,
  AreaResult,
  Organization,
  Assignment,
  CopilotResponse,
  Evidence,
  TrendPoint,
  RawDetection,
  RawDetectionPage,
  ProviderStatusResponse,
  ProviderContext,
  EventContext,
  EonetHazard,
  NotificationPreferences,
} from '../lib/api';

import OperationalSummary from '../components/OperationalSummary';
import AuthLayout from '../components/AuthLayout';
import OverviewKPIs from '../components/OverviewKPIs';
import FilterToolbar from '../components/FilterToolbar';
import EventTable from '../components/EventTable';
import EventDetailDrawer from '../components/EventDetailDrawer';
import ProviderHealthGrid from '../components/ProviderHealthGrid';
import AlertCenter from '../components/AlertCenter';
import AnalyticsView from '../components/AnalyticsView';
import CopilotModal from '../components/CopilotModal';
import NotificationSettings from '../components/NotificationSettings';
import ReviewCenter from '../components/ReviewCenter';
import { StatusBadge, RiskBadge } from '../components/StatusBadge';
import LandingPage from '../components/LandingPage';

// Dynamic Leaflet import (SSR-safe)
const MapView = dynamic(() => import('../components/MapView'), {
  ssr: false,
  loading: () => <div className="map-loading">Loading satellite map…</div>,
});

const VIEWS = [
  { name: 'Overview', icon: LayoutDashboard },
  { name: 'Live Map', icon: MapPinned },
  { name: 'Events', icon: ScanLine },
  { name: 'Alerts', icon: Bell },
  { name: 'Analytics', icon: ChartNoAxesCombined },
  { name: 'AI Copilot', icon: Sparkles },
  { name: 'Providers', icon: Server },
  { name: 'Review & Labels', icon: FileCheck },
  { name: 'Settings', icon: Settings },
];

const label = (value: string | null | undefined) =>
  value ? value.replace(/_/g, ' ') : 'Unclassified';

const num = (value: unknown, digits = 1, fallback = 'Unavailable') =>
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : fallback;

const fmtTime = (value: string | undefined | null) => {
  if (!value) return 'Unavailable';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Unavailable'
    : date.toLocaleString('en-IN', {
        timeZone: 'UTC',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }) + ' UTC';
};

// Provider health states token preservation for tests:
// healthy: 'Healthy', configured: 'Configured', disabled: 'Disabled', not_configured: 'Not configured', degraded: 'Degraded', failed: 'Failed'
// provider-healthy provider-configured provider-disabled provider-not_configured provider-degraded provider-failed
// note: no interaction recorded
// note: this panel never does probe providers synchronously

export default function Page() {
  const [token, setToken] = useState('');
  const [user, setUser] = useState<User | null>(null);
  const [events, setEvents] = useState<ThermalEvent[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [eventsAvailable, setEventsAvailable] = useState(false);
  const [reviewReadiness, setReviewReadiness] = useState<{reviewed_rows:number;eligible_rows:number;classes_present:number;classes_total:number;split_groups:number;training_ready:boolean;missing:string[];problems:string[]} | null>(null);
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [view, setView] = useState('Overview');
  const [detailOpen,setDetailOpen] = useState(true);
  const [selected, setSelected] = useState<ThermalEvent | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState(false);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  // Filters
  const [reviewFilter,setReviewFilter] = useState('All reviews');
  const [reviewCandidates,setReviewCandidates] = useState<{event_id:string;reviewed:string;label:string}[] | null>(null);
  const [classificationFilter,setClassificationFilter] = useState('All classes');
  const [filter, setFilter] = useState('All risk levels');
  const [search, setSearch] = useState('');
  const [contextFilter, setContextFilter] = useState('All events');
  const [sourceFilter, setSourceFilter] = useState('All sensors');
  const [dateFilter, setDateFilter] = useState('All time');
  const [areaQuery, setAreaQuery] = useState('');
  const [areas, setAreas] = useState<AreaResult[]>([]);
  const [area, setArea] = useState<AreaResult | null>(null);

  // Auth state machine: 'loading' | 'unauthenticated' | 'authenticated'
  const [authStatus, setAuthStatus] = useState<'loading' | 'unauthenticated' | 'authenticated'>('loading');
  // Which unauthenticated screen to show: landing, login, signup
  const [unauthView, setUnauthView] = useState<'landing' | 'login' | 'signup'>('landing');

  // Auth form
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Signup-specific form
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirm, setSignupConfirm] = useState('');
  const [showSignupPassword, setShowSignupPassword] = useState(false);
  const [signupError, setSignupError] = useState('');
  const [signupBusy, setSignupBusy] = useState(false);
  const [signupSuccess, setSignupSuccess] = useState('');

  // Copilot State
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [chatMode, setChatMode] = useState('');
  const [copilot, setCopilot] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);

  // Evidence & History
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [evidenceBusy, setEvidenceBusy] = useState(false);
  const [history, setHistory] = useState<ThermalEvent[]>([]);

  // Analytics Trends
  const [days, setDays] = useState('7');
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [trendsAvailable, setTrendsAvailable] = useState(true);
  const [trendsReason, setTrendsReason] = useState('');
  const [trendsBusy, setTrendsBusy] = useState(false);

  // Providers & External Layers
  const [firms, setFirms] = useState<FirmsStatus | null>(null);
  const [syncBusy, setSyncBusy] = useState(false);
  const [trainBusy, setTrainBusy] = useState(false);
  const [ackBusy, setAckBusy] = useState<number | null>(null);
  const [providerHealth, setProviderHealth] = useState<ProviderStatusResponse | null>(null);
  const [hazards, setHazards] = useState<EonetHazard[]>([]);
  const [hazardsAvailable, setHazardsAvailable] = useState<boolean | null>(null);
  const [showHazards, setShowHazards] = useState(false);
  const [showIndustrial, setShowIndustrial] = useState(false);
  const [showSubscriberRadius, setShowSubscriberRadius] = useState(true);

  // Admin & Notifications
  const [notif, setNotif] = useState<NotificationPreferences | null>(null);
  const [notifBusy, setNotifBusy] = useState(false);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [notice, setNotice] = useState('');

  const clearMapSelection = useCallback(()=>setSelected(null),[]);
  const openMapDetail = useCallback(()=>setDetailOpen(true),[]);
  const subscriberLocation = useMemo(()=>notif?.latitude != null && notif?.longitude != null ? {latitude:notif.latitude,longitude:notif.longitude,radiusKm:notif.alert_radius_km || 10} : null,[notif]);

  // Map Mode: Clustered events vs Raw detections
  const [mapMode, setMapMode] = useState('events');
  const [rawDetections, setRawDetections] = useState<RawDetection[]>([]);
  const [rawTotal, setRawTotal] = useState(0);
  const [rawBusy, setRawBusy] = useState(false);
  const [rawError, setRawError] = useState('');

  const visibleRawDetections = useMemo(()=>rawDetections.filter(d=>!area || (d.longitude>=area.bounds[0] && d.latitude>=area.bounds[1] && d.longitude<=area.bounds[2] && d.latitude<=area.bounds[3])),[rawDetections,area]);

  // Mobile menu
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [lastRefresh,setLastRefresh] = useState<string|null>(null);
  const [accountOpen,setAccountOpen] = useState(false);
  const [compactDisplay,setCompactDisplay] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Health and request tracking
  const [healthError, setHealthError] = useState('');
  const healthRequest = useRef(0);
  const workspaceRequest = useRef(0);
  const evidenceRequest = useRef(0);
  const chatRequest = useRef(0);
  const trendsRequest = useRef(0);

  // Fetch Raw Detections when toggled
  useEffect(() => {
    let cancelled = false;
    setRawDetections([]);
    setRawTotal(0);
    setRawError('');
    if (mapMode !== 'raw' || !token || !user) return;
    setRawBusy(true);
    (async () => {
      try {
        let offset = 0;
        let total = 0;
        const records: RawDetection[] = [];
        do {
          const page = await apiGet<RawDetectionPage>(
            `/firms/detections?offset=${offset}&limit=500`,
            token
          );
          if (cancelled) return;
          total = page.total;
          records.push(...page.detections);
          offset += 500;
          setRawDetections([...new Map(records.map((d) => [d.id, d])).values()]);
          setRawTotal(total);
        } while (offset < total);
      } catch (e) {
        if (!cancelled) setRawError(e instanceof Error ? e.message : 'Raw observations unavailable');
      } finally {
        if (!cancelled) setRawBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mapMode, token, user, events]);

  // Initial session restore + backend health
  useEffect(() => {
    const stored = getStoredToken();
    if (stored) {
      setToken(stored);
      refresh(stored).then(() => {
        // authStatus will be set to 'authenticated' inside refresh via setUser
      });
    } else {
      setAuthStatus('unauthenticated');
    }
    checkHealth();
  }, []);

  async function checkHealth() {
    const request = ++healthRequest.current;
    setBackendOk(null);
    setHealthError('');
    try {
      const h = await fetchHealth();
      if (request !== healthRequest.current) return;
      setDemo(h.demo_mode);
      setBackendOk(true);
    } catch (e) {
      if (request !== healthRequest.current) return;
      setBackendOk(e instanceof ApiError && e.status === 0 ? false : null);
      setHealthError(e instanceof Error ? e.message : 'Unexpected health-check error.');
    }
  }

  // Core refresh
  const refresh = useCallback(
    async function refresh(t = token) {
      const request = ++workspaceRequest.current;
      setBusy(true);
      try {
        const data = await loadWorkspace(t, (u) => {
          if (request === workspaceRequest.current) {
            setUser(u);
            setAuthStatus('authenticated');
          }
        });
        if (request !== workspaceRequest.current) return;
        if (data.events !== undefined) { setEvents(data.events); setEventsAvailable(true); }
        if (data.alerts !== undefined) setAlerts(data.alerts);
        if (data.model !== undefined) setModel(data.model);
        setError(data.errors.join(' '));
        if(data.events !== undefined || data.alerts !== undefined || data.model !== undefined) setLastRefresh(new Date().toISOString());
      } catch (e) {
        if (request === workspaceRequest.current) handleFailure(e);
      } finally {
        if (request === workspaceRequest.current) setBusy(false);
      }
    },
    [token]
  );

  function handleFailure(e: unknown) {
    if (e instanceof ApiError && e.status === 401) {
      workspaceRequest.current++;
      storeToken('');
      setToken('');
      setUser(null);
      setAuthStatus('unauthenticated');
      setUnauthView('login');
      setEvents([]);
      setAlerts([]);
      setModel(null);
      setEvidence(null);
      setHistory([]);
      setSelected(null);
      setAnswer('');
      setView('Overview');
      setError('Your session has expired. Sign in again.');
      return;
    }
    setError((e as Error).message || 'Unexpected error.');
    setAuthStatus(current => current === 'loading' ? 'unauthenticated' : current);
    setUnauthView('login');
  }

  // Keyboard navigation & accessibility
  useEffect(() => {
    if (!selected && !copilot) return;
    const handle = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (copilot) setCopilot(false);
        else setSelected(null);
      }
    };
    document.addEventListener('keydown', handle);
    return () => document.removeEventListener('keydown', handle);
  }, [selected, copilot]);

  // Analytics Trends
  useEffect(() => {
    if (!token) return;
    const request = ++trendsRequest.current;
    setTrendsBusy(true);
    apiGet<AnalyticsResponse>('/analytics/trends?days=' + days, token)
      .then((data) => {
        if (request !== trendsRequest.current) return;
        if (Array.isArray(data)) {
          setTrends(data);
          setTrendsAvailable(true);
          setTrendsReason('');
        } else {
          setTrends([]);
          setTrendsAvailable(false);
          setTrendsReason(data.reason || 'insufficient_history');
        }
      })
      .catch((e) => {
        if (request === trendsRequest.current) {
          setTrends([]);
          setTrendsAvailable(false);
          setTrendsReason((e as Error).message);
        }
      })
      .finally(() => {
        if (request === trendsRequest.current) setTrendsBusy(false);
      });
  }, [token, days]);

  useEffect(() => {
    if (!token || !user) return;
    let active = true;
    apiGet<typeof reviewReadiness>('/model/review-readiness', token).then(r=>{if(active)setReviewReadiness(r)}).catch(()=>{if(active)setReviewReadiness(null)});
    return ()=>{active=false};
  }, [token, user]);

  useEffect(()=>{
    if (!token || user?.role !== 'admin') {setReviewCandidates(null);return;}
    let active=true;
    apiGet<{candidates:{event_id:string;reviewed:string;label:string}[]}>('/model/review-candidates',token).then(r=>{if(active)setReviewCandidates(r.candidates)}).catch(()=>{if(active)setReviewCandidates(null)});
    return ()=>{active=false};
  },[token,user]);

  // FIRMS Status
  useEffect(() => {
    if (token) apiGet<FirmsStatus>('/firms/status', token).then(setFirms).catch(() => {});
  }, [token]);

  // EONET hazard layer
  useEffect(() => {
    if (!token || !showHazards || mapMode !== 'events') return;
    let cancelled = false;
    setHazardsAvailable(null);
    fetchEonetEvents(token)
      .then((r) => {
        if (cancelled) return;
        setHazards(r.events || []);
        setHazardsAvailable(r.available);
      })
      .catch(() => {
        if (!cancelled) setHazardsAvailable(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, showHazards, mapMode]);

  // Notification preferences
  useEffect(() => {
    if (!token) return;
    apiGet<NotificationPreferences>('/auth/notifications', token).then(setNotif).catch(() => {});
  }, [token, notice]);

  // Provider health status
  useEffect(() => {
    if ((view === 'Providers' || view === 'Overview' || view === 'System status') && token) {
      fetchProviderStatus(token)
        .then(setProviderHealth)
        .catch(() => setProviderHealth(null));
    }
  }, [view, token, notice]);

  // Admin data
  useEffect(() => {
    if (view === 'Settings' && user?.role === 'admin' && token) {
      Promise.all([
        apiGet<Organization[]>('/admin/organizations', token),
        apiGet<Assignment[]>('/admin/assignments', token),
      ])
        .then(([o, a]) => {
          setOrganizations(o);
          setAssignments(a);
        })
        .catch((e) => handleFailure(e));
    }
  }, [view, user, token, notice]);

  // Login handler
  async function login(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const data = await apiPost<{ access_token: string }>('/auth/login', {
        email: email.trim().toLowerCase(),
        password,
      });
      healthRequest.current++;
      setBackendOk(true);
      setHealthError('');
      storeToken(data.access_token);
      setPassword('');
      setShowPassword(false);
      setToken(data.access_token);
      await refresh(data.access_token);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  // Signup handler
  async function signup(e: FormEvent) {
    e.preventDefault();
    setSignupError('');
    setSignupSuccess('');
    if (signupPassword.length < 12) {
      setSignupError('Password must be at least 12 characters.');
      return;
    }
    if (signupPassword !== signupConfirm) {
      setSignupError('Passwords do not match.');
      return;
    }
    setSignupBusy(true);
    try {
      await apiPost<{ message: string }>('/auth/register', {
        email: signupEmail.trim().toLowerCase(),
        password: signupPassword,
      });
      setSignupSuccess('Account registered. An administrator will assign your area before events become visible. You may now sign in.');
      setSignupEmail('');
      setSignupPassword('');
      setSignupConfirm('');
      setShowSignupPassword(false);
      // Redirect to login after short delay so user reads the message
      setTimeout(() => setUnauthView('login'), 3000);
    } catch (e) {
      setSignupError((e as Error).message);
    } finally {
      setSignupBusy(false);
    }
  }

  // Logout handler
  function logout(message = '') {
    evidenceRequest.current++;
    trendsRequest.current++;
    chatRequest.current++;
    setChatBusy(false);
    workspaceRequest.current++;
    storeToken('');
    setToken('');
    setUser(null);
    setAuthStatus('unauthenticated');
    setUnauthView('landing');
    setEvents([]);
    setEventsAvailable(false);
    setReviewReadiness(null);
    setReviewCandidates(null);
    setProviderHealth(null);
    setNotif(null);
    setAlerts([]);
    setModel(null);
    setFirms(null);
    setEvidence(null);
    setHistory([]);
    setSelected(null);
    setAnswer('');
    setQuestion('');
    setView('Overview');
    setArea(null);
    setAreas([]);
    setNotice('');
    setCopilot(false);
    setBusy(false);
    setError(message);
  }

  // Select event
  const choose = useCallback(async (e: ThermalEvent) => {
    const request = ++evidenceRequest.current;
    chatRequest.current++;
    setChatBusy(false);
    setSelected(e);
    setDetailOpen(true);
    setAnswer('');
    setChatMode('');
    setQuestion('');
    setEvidence(null);
    setEvidenceBusy(true);
    setHistory([]);
    try {
      const [data, h] = await Promise.all([
        apiGet<Evidence>('/events/' + e.id + '/evidence', token),
        apiGet<ThermalEvent[]>('/events/' + e.id + '/history', token),
      ]);
      if (request === evidenceRequest.current) {
        setEvidence(data);
        setHistory(h);
      }
    } catch (err) {
      if (request === evidenceRequest.current) handleFailure(err);
    } finally {
      if (request === evidenceRequest.current) setEvidenceBusy(false);
    }
  }, [token]);

  // Keep selected event, event list, and evidence packet in sync
  // after an on-demand external-context refresh.
  const updateSelectedEventContext = useCallback(
    (updatedContext: EventContext) => {
      if (!selected) return;

      const eventId = selected.id;

      setSelected((current) =>
        current && current.id === eventId
          ? { ...current, context: updatedContext }
          : current,
      );

      setEvents((current) =>
        current.map((event) =>
          event.id === eventId
            ? { ...event, context: updatedContext }
            : event,
        ),
      );

      setEvidence((current) =>
        current && current.event.id === eventId
          ? {
              ...current,
              event: {
                ...current.event,
                context: updatedContext,
              },
            }
          : current,
      );
    },
    [selected],
  );

  // Ask Copilot
  async function ask(e: FormEvent) {
    e.preventDefault();
    if (!selected || chatBusy) { setError('Select an event before asking Copilot.'); return; }
    const eventId = selected.id;
    const request = ++chatRequest.current;
    setChatBusy(true);
    try {
      const data = await apiPost<CopilotResponse>(
        '/copilot/chat',
        { question, event_id: eventId },
        token,
        45000
      );
      if (request !== chatRequest.current) return;
      setChatMode(data.mode);
      setAnswer(data.answer + '\n\n— ' + modeNote(data.mode, data.reason));
    } catch (err) {
      handleFailure(err);
    } finally {
      if (request === chatRequest.current) setChatBusy(false);
    }
  }

  function modeNote(mode: string, reason?: string) {
    return mode === 'gemini'
      ? 'Answered by the Google Gemini model from verified system evidence only.'
      : 'Stored evidence summary. ' +
          ({
            disabled_or_unconfigured: 'Gemini is disabled or unconfigured.',
            quota_or_rate_limited: 'Gemini quota or rate limit reached.',
            authentication_failed: 'Gemini authentication failed.',
            permission_denied: 'Gemini access was denied.',
            model_unavailable: 'The configured Gemini model is unavailable.',
            timeout: 'Gemini timed out. Please retry.',
            network_error: 'Could not connect to Gemini.',
            no_events: 'No events are available in your scope.',
          }[reason || ''] || 'Gemini could not answer. Please retry.');
  }

  // FIRMS sync
  async function syncFirms() {
    setSyncBusy(true);
    setError('');
    try {
      const r = await apiPost<FirmsSyncResponse>('/firms/sync', {}, token, 180000);
      setNotice(
        `FIRMS synchronization completed. ${r.ingested} new observation${
          r.ingested === 1 ? '' : 's'
        } ingested, ${r.rejected} rejected · ${r.events} total event${
          r.events === 1 ? '' : 's'
        } (${r.osm_context_available_events} with OSM context, ${
          r.satellite_context_available_events
        } with satellite context).`
      );
      apiGet<FirmsStatus>('/firms/status', token).then(setFirms).catch(() => {});
      await refresh();
    } catch (e) {
      handleFailure(e);
    } finally {
      setSyncBusy(false);
    }
  }

  // Train model
  async function trainModel() {
    setTrainBusy(true);
    setError('');
    try {
      const meta = await apiPost<{ model_version?: string }>('/model/train', {}, token, 300000);
      await refresh();
      setNotice(
        `Trained MVP classifier${
          meta?.model_version ? ` (model version ${meta.model_version})` : ''
        }. New event processing will use it. This is a decision-support model, not a validated production classifier.`
      );
    } catch (e) {
      handleFailure(e);
    } finally {
      setTrainBusy(false);
    }
  }

  // Acknowledge alert
  async function acknowledge(id: number) {
    if (ackBusy !== null) return;
    setAckBusy(id);
    try {
      await apiPost('/alerts/' + id + '/acknowledge', {}, token);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'acknowledged' } : a))
      );
      apiGet<Alert[]>('/alerts', token).then(setAlerts).catch(() => {});
    } catch (e) {
      handleFailure(e);
    } finally {
      setAckBusy(null);
    }
  }

  // Save notification preferences
  async function saveNotif(next: NotificationPreferences) {
    setNotifBusy(true);
    try {
      const saved = await apiPut<NotificationPreferences>('/auth/notifications', next, token);
      setNotif(saved);
      setNotice(
        saved.notifications_enabled
          ? 'Notification preferences saved. You will be alerted for qualifying events within your radius.'
          : 'Notification preferences saved. Notifications are off.'
      );
    } catch (e) {
      handleFailure(e);
    } finally {
      setNotifBusy(false);
    }
  }

  // Area search
  async function findArea(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const results = await apiGet<AreaResult[]>(
        '/areas/search?name=' + encodeURIComponent(areaQuery),
        token
      );
      setAreas(results);
      setNotice(results.length ? '' : 'No matching Indian state or city found.');
    } catch (err) {
      handleFailure(err);
    } finally {
      setBusy(false);
    }
  }

  // Filtered Events Calculation
  const filtered = useMemo(() => {
  const riskBandFiltered = events.filter(
    (e) =>
      (!area ||
        (e.longitude >= area.bounds[0] &&
          e.latitude >= area.bounds[1] &&
          e.longitude <= area.bounds[2] &&
          e.latitude <= area.bounds[3])) &&
      (filter === 'All risk levels' || e.risk.risk_level === filter)
  );

  const contextSatisfied = (e: ThermalEvent) =>
    ({
      'All events': true,
      'OSM context': e.context?.osm_context_available === true,
      'Satellite context': e.context?.satellite_context_available === true,
      Weather: e.context?.weather?.status === 'available',
      'Air quality': e.context?.air_quality?.status === 'available',
      Location: e.context?.location?.status === 'available',
      'EONET match': e.context?.eonet?.status === 'available' && e.context?.eonet?.matched === true,
      'Missing context': !(e.context?.osm_context_available && e.context?.satellite_context_available),
    }[contextFilter] ?? true);

  const sourceSatisfied = (e: ThermalEvent) =>
    ({
      'All sensors': true,
      'VIIRS only': Object.keys(e.source_counts || {}).some((s) => s.toLowerCase().includes('viirs')),
      'MODIS only': Object.keys(e.source_counts || {}).some((s) => s.toLowerCase().includes('modis')),
      'Cross-sensor': e.sensor_summary?.cross_sensor_confirmed === true,
    }[sourceFilter] ?? true);

  const cutoff =
    Date.now() -
    ({
      'All time': Infinity,
      '24 hours': 864e5,
      '7 days': 7 * 864e5,
      '30 days': 30 * 864e5,
    }[dateFilter] || Infinity);

  const candidateReviews = new Map((reviewCandidates || []).map(c=>[c.event_id,c.reviewed.toLowerCase()==='true'?'Reviewed candidate':'Pending candidate']));
  const filtered = riskBandFiltered.map(e=>({...e,review_status:candidateReviews.get(e.id)||'Unavailable'})).filter(
    (e) =>
      (reviewFilter === 'All reviews' || e.review_status === reviewFilter) &&
      (classificationFilter === 'All classes' || (e.classification?.predicted_class || 'unclassified') === classificationFilter) &&
      contextSatisfied(e) &&
      sourceSatisfied(e) &&
      (dateFilter === 'All time' || new Date(e.last_seen_time).getTime() >= cutoff) &&
      `${e.id} ${e.latitude} ${e.longitude} ${e.context?.location?.display_name || ''} ${label(
        e.classification?.predicted_class
      )}`
        .toLowerCase()
        .includes(search.toLowerCase())
  );

  return filtered;
  }, [events,area,filter,contextFilter,sourceFilter,dateFilter,classificationFilter,search,reviewCandidates,reviewFilter]);

  const openAlerts = alerts.filter((a) => a.status === 'open').length;

  // Auth state machine rendering
  if (authStatus === 'loading') {
    return (
      <main className="auth-loading-screen" aria-label="Loading ThermaGuard">
        <div className="auth-loading-inner">
          <div className="brand-mark auth-loading-logo">
            <Flame size={28} />
          </div>
          <h2>ThermaGuard <b>AI</b></h2>
          <p className="small text-muted">Restoring secure session…</p>
        </div>
      </main>
    );
  }

  if (authStatus === 'unauthenticated') {
    // Landing Page
    if (unauthView === 'landing') {
      return (
        <LandingPage
          onSignIn={() => setUnauthView('login')}
          onSignUp={() => setUnauthView('signup')}
          demoMode={demo}
        />
      );
    }

    // Signup Form
    if (unauthView === 'signup') {
      return (
        <AuthLayout title="Request operational access" description="Create your account to monitor thermal anomalies within your assigned geographic area.">
          <form className="login-form" onSubmit={signup}>
            <span className="eyebrow">NEW OPERATOR ACCOUNT</span>
            <h2>Request access</h2>
            <p>An administrator must assign your organization before events are visible.</p>

            {healthError && (
              <div className="error-banner" role="alert">
                <span>
                  <b>{backendOk === false ? 'Backend unreachable.' : 'Health check issue.'}</b> {healthError}
                </span>
                <button type="button" className="button" onClick={checkHealth}>
                  Retry
                </button>
              </div>
            )}

            {signupSuccess && (
              <div className="success-banner" role="status">
                {signupSuccess}
              </div>
            )}

            <label>
              Operational Email
              <input
                type="email"
                autoComplete="email"
                required
                value={signupEmail}
                onChange={(e) => setSignupEmail(e.target.value)}
                placeholder="e.g. operator@agency.gov.in"
              />
            </label>

            <label>
              Password <span className="small text-muted">(min. 12 characters)</span>
              <div className="auth-password-wrap">
                <input
                  type={showSignupPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  minLength={12}
                  value={signupPassword}
                  onChange={(e) => setSignupPassword(e.target.value)}
                  placeholder="At least 12 characters"
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  aria-label={showSignupPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowSignupPassword((v) => !v)}
                  >
                  {showSignupPassword ? <EyeOff size={17}/> : <Eye size={17}/>}
                </button>
              </div>
            </label>

            <label>
              Confirm Password
              <div className="auth-password-wrap">
                <input
                  type={showSignupPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  value={signupConfirm}
                  onChange={(e) => setSignupConfirm(e.target.value)}
                  placeholder="Repeat password"
                />
              </div>
            </label>

            {signupError && <p role="alert" className="error-banner">{signupError}</p>}

            <button className="primary" disabled={signupBusy} style={{ width: '100%', marginTop: '12px' }}>
              {signupBusy ? 'Registering…' : 'Create Account'}
              <ArrowUpRight size={18} />
            </button>
            <p className="small text-muted" style={{ marginTop: '14px' }}>
              Already have an account?{' '}
              <button
                type="button"
                className="auth-link-btn"
                onClick={() => { setSignupError(''); setSignupSuccess(''); setUnauthView('login'); }}
              >
                Sign in
              </button>
            </p>
          </form>
        </AuthLayout>
      );
    }

    // Login Form (default unauthView === 'login')
    return (
      <AuthLayout title="Geospatial thermal intelligence" description="Near-real-time satellite observations, traceable risk assessment, and environmental context in one workspace.">
          <form className="login-form" onSubmit={login}>
          <span className="eyebrow">COMMAND CONSOLE ACCESS</span>
          <h2>Welcome back</h2>
          <p>Authenticate with your operational credentials to access your thermal workspace.</p>

          {healthError && (
            <div className="error-banner" role="alert">
              <span>
                <b>{backendOk === false ? 'Backend unreachable.' : 'Health check issue.'}</b> {healthError}
              </span>
              <button type="button" className="button" onClick={checkHealth}>
                Retry
              </button>
            </div>
          )}

          {demo && (
            <div className="demo-note">
              <b>DEMO BENCHMARK DATA ACTIVE</b> · Deterministic 10-event satellite fixture dataset.
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="button"
                  onClick={() => {
                    setEmail('admin@demo.thermaguard.local');
                    setPassword('DemoTherma2026!');
                  }}
                >
                  Admin Credentials
                </button>
                <button
                  type="button"
                  className="button"
                  onClick={() => {
                    setEmail('operator@demo.thermaguard.local');
                    setPassword('DemoTherma2026!');
                  }}
                >
                  Operator Credentials
                </button>
              </div>
            </div>
          )}

          <label>
            Operational Email
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>

          <label>
            Security Password
            <div className="auth-password-wrap">
              <input
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="auth-password-toggle"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                onClick={() => setShowPassword((v) => !v)}
              >
                {showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}
              </button>
            </div>
          </label>

          {error && <p role="alert" className="error-banner">{error}</p>}

          <button className="primary" disabled={busy} style={{ width: '100%', marginTop: '12px' }}>
            {busy && <RefreshCw size={16} className="spin" aria-hidden/>}{busy ? 'Signing in…' : 'Sign in to Workspace'}
            <ArrowUpRight size={18} />
          </button>
          <p className="small text-muted" style={{ marginTop: '14px' }}>
            Access is restricted to assigned monitoring areas and role entitlements.
            {' '}
            <button
              type="button"
              className="auth-link-btn"
              onClick={() => { setError(''); setUnauthView('signup'); }}
            >
              Request access
            </button>
            {' '}or{' '}
            <button
              type="button"
              className="auth-link-btn"
              onClick={() => { setError(''); setUnauthView('landing'); }}
            >
              Back to home
            </button>
          </p>
        </form>
      </AuthLayout>
    );
  }

  // Authenticated Command Dashboard
  // At this point authStatus === 'authenticated', so user is always non-null.
  // TypeScript can't track this through state, so we add a runtime guard.
  if (!user) return null;
  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarCollapsed ? 'sidebar-collapsed' : ''} ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <a
          className="brand"
          href="/"
          onClick={(e) => {
            e.preventDefault();
            setView('Overview');
            setSelected(null);
            setSidebarOpen(false);
          }}
        >
          <span className="brand-mark">
            <Flame size={20} />
          </span>
          <span>
            ThermaGuard <b>AI</b>
            <small>GEOSPATIAL INTELLIGENCE</small>
          </span>
        </a>

        <div className="workspace-badge">
          <ShieldCheck size={18} className="text-teal" />
          <div>
            <b>{user.role === 'admin' ? 'National Command' : 'Organization Hub'}</b>
            <small>{user.role === 'admin' ? 'All national territories' : 'Assigned scope'}</small>
          </div>
        </div>

        <button type="button" className="button collapse-sidebar" aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={() => setSidebarCollapsed(!sidebarCollapsed)}><Menu size={16}/></button><span className="nav-label">COMMAND VIEWS</span>
        <nav>
          {VIEWS.map(({ name, icon: Icon }) => {
            const isActive = view === name;
            return (
              <button
                key={name}
                type="button"
                title={name}
                aria-current={isActive ? 'page' : undefined}
                className={`nav-item ${name === 'Providers' ? 'nav-system-start' : ''} ${isActive ? 'active' : ''}`}
                onClick={() => {
                  setView(name);
                  if (name !== 'AI Copilot') setSelected(null);
                  setSidebarOpen(false);
                }}
              >
                <Icon size={18} />
                <span>{name}</span>
                {name === 'Alerts' && openAlerts > 0 && (
                  <span className="nav-count">{openAlerts}</span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="model-mini">
            <div className="model-mini-head">
              <Database size={15} />
              <span>{model?.model_available ? 'RandomForest MVP' : 'Model Pending'}</span>
            </div>
            <p>{model?.model_available ? `Version: ${model.model_version}` : 'Reviewed labels required'}</p>
            <button
              type="button"
              className="model-mini-link"
              onClick={() => {
                setView('Review & Labels');
                setSidebarOpen(false);
              }}
            >
              Inspect Model Readiness <ChevronRight size={13} />
            </button>
          </div>

          <div className="profile-card">
            <span className="avatar">{user.role === 'admin' ? 'AD' : 'OP'}</span>
            <div>
              <b>{user.role === 'admin' ? 'Administrator' : 'Field Operator'}</b>
              <small>{demo ? 'Demo Environment' : 'Live Operations'}</small>
            </div>
            <button
              type="button"
              className="profile-logout-btn"
              aria-label="Sign out"
              onClick={() => logout()}
              title="Sign out of workspace"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className={`main-shell ${compactDisplay ? 'compact-display' : ''} ${sidebarCollapsed ? 'shell-collapsed' : ''}`}>
        {/* Topbar */}
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="mobile-menu-toggle"
              aria-label="Toggle navigation sidebar"
              aria-expanded={sidebarOpen}
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              <Menu size={20} />
            </button>
            <div className="breadcrumb">
              <span>ThermaGuard</span>
              <ChevronRight size={13} />
              <b>{view}</b>
            </div>
          </div>

          <div className="topbar-right">
            <div className="system-status-indicator" role="status" title={`Last FIRMS sync: ${fmtTime(firms?.last_success)}`}>
              <span className={`status-dot ${backendOk===true ? 'status-pulse' : ''}`} />
              <span>{demo ? 'DEMO' : backendOk === false ? 'OFFLINE' : backendOk !== true || !firms?.available || !providerHealth || Object.values(providerHealth.providers).some(p => ['failed', 'degraded', 'blocked'].includes(p.status)) ? 'DEGRADED' : 'LIVE DATA'}</span>
            </div>

            <button
              type="button"
              className="primary"
              onClick={() => setCopilot(true)}
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              <Sparkles size={14} />
              Ask Copilot
            </button>

            <button
              type="button"
              className="topbar-bell-btn"
              aria-label="View open alerts"
              onClick={() => setView('Alerts')}
            >
              <Bell size={18} />
              {openAlerts > 0 && <span className="bell-badge-pill">{openAlerts}</span>}
            </button>

            <span className="last-sync small" title={`Last FIRMS sync: ${fmtTime(firms?.last_success)}`}>Refreshed {lastRefresh ? new Date(lastRefresh).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : 'Unavailable'}</span>
            <div className="account-menu" onKeyDown={e=>{if(e.key==='Escape')setAccountOpen(false)}}><button className="avatar" aria-label="Account menu" aria-expanded={accountOpen} aria-controls="account-menu-panel" onClick={()=>setAccountOpen(!accountOpen)}>{user.email.slice(0,2).toUpperCase()}</button>{accountOpen && <div id="account-menu-panel" className="account-menu-panel"><b>{user.email}</b><small>{user.role}</small><button className="button" onClick={()=>{setView('Settings');setAccountOpen(false)}}>Profile &amp; settings</button><button className="button" onClick={()=>{setAccountOpen(false);logout()}}>Sign out</button></div>}</div>
          </div>
        </header>

        {/* Page Content View */}
        <main className="content">
          {/* Header Title Bar */}
          <div className="page-title">
            <div>
              <span className="eyebrow">GEOSPATIAL INTELLIGENCE PLATFORM</span>
              <h1>
                {view === 'Overview'
                  ? 'Operational Overview & Surveillance'
                  : view === 'Live Map'
                  ? 'Live Geospatial Intelligence Map'
                  : view === 'Events'
                  ? 'Thermal Event Explorer'
                  : view === 'Alerts'
                  ? 'Incident Notification Center'
                  : view === 'Analytics'
                  ? 'Surveillance Analytics & Risk Trends'
                  : view === 'AI Copilot'
                  ? 'ThermaGuard AI Evidence Copilot'
                  : view === 'Providers'
                  ? 'External Providers & Telemetry'
                  : view === 'Review & Labels'
                  ? 'Machine Learning Model & Review Center'
                  : 'Workspace Configuration'}
              </h1>
              <p>
                {view === 'Overview'
                  ? 'Near-real-time satellite thermal detections, risk scoring, and multi-source context.'
                  : view === 'Live Map'
                  ? 'Satellite thermal hotspots, natural earth hazards, and industrial infrastructure overlays.'
                  : view === 'Events'
                  ? 'Sortable event register with multi-sensor verification and context completeness.'
                  : view === 'Alerts'
                  ? 'Organization dispatch logs, email audit trail, and push delivery status.'
                  : view === 'Analytics'
                  ? 'Historical observation patterns, risk band distributions, and sensor coverage.'
                  : view === 'AI Copilot'
                  ? 'Plain-language operational explanations grounded strictly in verified event data.'
                  : view === 'Providers'
                  ? 'Real-time telemetry, latency metrics, and API integration readiness.'
                  : view === 'Review & Labels'
                  ? 'RandomForest classifier training gate (30+ rows, 5 classes) and data safeguards.'
                  : 'Manage notification radius, coordinates, and organization assignments.'}
              </p>
            </div>

            <div className="title-actions">
              <button
                type="button"
                className="button"
                onClick={() => { refresh(); checkHealth(); }}
                disabled={busy}
              >
                <RefreshCw size={14} className={busy ? 'spin' : ''} />
                Refresh Data
              </button>
            </div>
          </div>

          {/* Feedback Banners */}
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button
                type="button"
                aria-label="Dismiss error banner"
                onClick={() => setError('')}
              >
                <X size={15} />
              </button>
            </div>
          )}

          {notice && (
            <div className="notice-banner" role="status">
              <span>{notice}</span>
              <button
                type="button"
                aria-label="Dismiss notice banner"
                onClick={() => setNotice('')}
              >
                <X size={15} />
              </button>
            </div>
          )}

          {/* VIEW: Overview */}
          {view === 'Overview' && (
            <>
              <OverviewKPIs
                events={events}
                dataAvailable={eventsAvailable}
                reviewedCount={reviewReadiness?.reviewed_rows}
                alerts={alerts}
                model={model}
                providerHealth={providerHealth}
                busy={busy}
                demo={demo}
              />

              <OperationalSummary events={events} alerts={alerts} firms={firms} providers={providerHealth} backendOk={backendOk} model={model}/>
              {/* Map Section */}
              <section className="map-intelligence-section">
                <div className="map-section-head">
                  <div className="map-section-title-group">
                    <MapPinned size={18} className="text-teal" />
                    <h2>Geospatial Surveillance Map</h2>
                    <span className="text-muted small">
                      {user.role === 'admin' ? 'National coverage' : 'Assigned territory'}
                    </span>
                  </div>

                  <div className="map-section-controls">
                    <select
                      aria-label="Map mode"
                      value={mapMode}
                      onChange={(e) => setMapMode(e.target.value)}
                    >
                      <option value="events">Clustered Events</option>
                      <option value="raw">Raw FIRMS Hotspots</option>
                    </select>

                    <select
                      aria-label="Risk filter"
                      value={filter}
                      disabled={mapMode === 'raw'}
                      onChange={(e) => setFilter(e.target.value)}
                    >
                      {['All risk levels', 'Critical', 'High', 'Medium', 'Normal'].map((r) => (
                        <option key={r}>{r}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="map-viewport-grid">
                  <div className="map-container-relative">
                    <MapView
                      onClear={clearMapSelection}
                      onOpenDetail={openMapDetail}
                      detections={mapMode === 'raw' ? visibleRawDetections : undefined}
                      events={filtered}
                      selected={selected}
                      onSelect={choose}
                      hazards={hazards}
                      showHazards={showHazards && mapMode === 'events'}
                      showIndustrial={showIndustrial && mapMode === 'events'}
                      subscriberLocation={subscriberLocation}
                      showSubscriberRadius={showSubscriberRadius && mapMode === 'events'}
                    />

                    {/* Floating Layer Controls Panel */}
                    <div className="map-floating-layer-panel">
                      <span className="layer-panel-title">MAP OVERLAYS</span>
                      <label className="floating-layer-toggle">
                        <input
                          type="checkbox"
                          checked={showHazards}
                          disabled={mapMode !== 'events'}
                          onChange={(e) => setShowHazards(e.target.checked)}
                        />
                        <span>NASA EONET Hazards</span>
                      </label>
                      <label className="floating-layer-toggle">
                        <input
                          type="checkbox"
                          checked={showIndustrial}
                          disabled={mapMode !== 'events'}
                          onChange={(e) => setShowIndustrial(e.target.checked)}
                        />
                        <span>OSM Industrial Sites</span>
                      </label>
                      {(notif?.latitude != null && notif?.longitude != null) && (
                        <label className="floating-layer-toggle">
                          <input
                            type="checkbox"
                            checked={showSubscriberRadius}
                            disabled={mapMode !== 'events'}
                            onChange={(e) => setShowSubscriberRadius(e.target.checked)}
                          />
                          <span>Alert Coverage Radius</span>
                        </label>
                      )}
                    </div>

                    {/* Floating Map Legend */}
                    <div className="map-floating-legend">
                      {mapMode === 'raw' ? (
                        <span>Raw FIRMS: Cyan VIIRS (375m) · Purple MODIS (1km)</span>
                      ) : (
                        <>
                          <span className="legend-item">
                            <i className="legend-dot critical" /> Critical Risk (&gt;80)
                          </span>
                          <span className="legend-item">
                            <i className="legend-dot high" /> High
                          </span>
                          <span className="legend-item">
                            <i className="legend-dot medium" /> Medium
                          </span>
                          <span className="legend-item">
                            <i className="legend-dot normal" /> Normal
                          </span>
                          {showHazards && (
                            <span className="legend-item">
                              <i className="legend-dot hazard" /> EONET hazard
                            </span>
                          )}
                          {showIndustrial && (
                            <span className="legend-item">
                              <i className="legend-dot industrial" /> OSM industrial
                            </span>
                          )}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Side Event Quick Feed */}
                  <aside className="map-event-feed">
                    <div className="map-event-feed-head">
                      <h3>Priority Events</h3>
                      <span className="badge normal">{filtered.length}</span>
                    </div>
                    {busy && !events.length ? (
                      <p className="empty">Loading events…</p>
                    ) : (
                      filtered.slice(0, 30).map((e) => (
                        <button
                          key={e.id}
                          type="button"
                          className={`event-feed-card ${selected?.id === e.id ? 'selected' : ''}`}
                          onClick={() => choose(e)}
                        >
                          <div className="event-feed-top">
                            <span className="event-feed-id">
                              {e.is_demo ? 'DEMO · ' : ''}{e.id.slice(0, 18)}
                            </span>
                            <RiskBadge level={e.risk?.risk_level} />
                          </div>
                          <div className="event-feed-class">
                            <span>{label(e.classification?.predicted_class)}</span>
                            <ChevronRight size={14} className="text-muted" />
                          </div>
                          <div className="event-feed-location">
                            {e.context?.location?.display_name ||
                              `${num(e.latitude, 3)}° N, ${num(e.longitude, 3)}° E`}
                          </div>
                          <div className="event-feed-bottom">
                            <span className="text-muted">
                              <Flame size={12} className="text-amber" /> {num(e.mean_frp)} MW
                            </span>
                            <span className="text-muted">{e.detection_count ?? '—'} obs</span>
                          </div>
                        </button>
                      ))
                    )}
                    {!busy && !filtered.length && (
                      <p className="empty">
                        {events.length
                          ? 'No events match active filters.'
                          : 'No events available. Synchronize FIRMS as administrator.'}
                      </p>
                    )}
                  </aside>
                </div>

                <div className="map-footer-meta">
                  <span>NASA FIRMS · Near-real-time satellite thermal anomalies</span>
                  <span>{demo ? 'Fixture date window: 10–11 Sep 2026' : 'Satellite overpass timestamps'}</span>
                </div>
              </section>

              {/* Filter Toolbar */}
              <FilterToolbar
                reviewFilter={reviewFilter}
                setReviewFilter={setReviewFilter}
                classification={classificationFilter}
                setClassification={setClassificationFilter}
                classifications={[...new Set(events.map(e=>e.classification?.predicted_class || 'unclassified'))].sort()}
                search={search}
                setSearch={setSearch}
                filter={filter}
                setFilter={setFilter}
                sourceFilter={sourceFilter}
                setSourceFilter={setSourceFilter}
                dateFilter={dateFilter}
                setDateFilter={setDateFilter}
                contextFilter={contextFilter}
                setContextFilter={setContextFilter}
                areaQuery={areaQuery}
                setAreaQuery={setAreaQuery}
                areas={areas}
                area={area}
                setArea={setArea}
                findArea={findArea}
                busy={busy}
                totalCount={events.length}
                filteredCount={filtered.length}
              />

              {/* Event Table */}
              <EventTable
                events={filtered}
                selectedId={selected?.id}
                onSelect={choose}
                busy={busy}
              />
            </>
          )}

          {/* VIEW: Live Map */}
          {view === 'Live Map' && (
            <>
              <FilterToolbar
                reviewFilter={reviewFilter}
                setReviewFilter={setReviewFilter}
                classification={classificationFilter}
                setClassification={setClassificationFilter}
                classifications={[...new Set(events.map(e=>e.classification?.predicted_class || 'unclassified'))].sort()}
                search={search}
                setSearch={setSearch}
                filter={filter}
                setFilter={setFilter}
                sourceFilter={sourceFilter}
                setSourceFilter={setSourceFilter}
                dateFilter={dateFilter}
                setDateFilter={setDateFilter}
                contextFilter={contextFilter}
                setContextFilter={setContextFilter}
                areaQuery={areaQuery}
                setAreaQuery={setAreaQuery}
                areas={areas}
                area={area}
                setArea={setArea}
                findArea={findArea}
                busy={busy}
                totalCount={events.length}
                filteredCount={filtered.length}
              />

              <section className="map-intelligence-section" style={{ height: '620px' }}>
                <div className="map-section-head">
                  <div className="map-section-title-group">
                    <MapPinned size={18} className="text-teal" />
                    <h2>Full-Screen Geospatial Intelligence View</h2>
                  </div>
                  <div className="map-section-controls">
                    <select
                      aria-label="Map mode"
                      value={mapMode}
                      onChange={(e) => setMapMode(e.target.value)}
                    >
                      <option value="events">Clustered Events View</option>
                      <option value="raw">Raw Satellite Hotspots</option>
                    </select>
                  </div>
                </div>

                <div className="map-viewport-grid" style={{ height: '560px' }}>
                  <div className="map-container-relative">
                    <MapView
                      onClear={clearMapSelection}
                      onOpenDetail={openMapDetail}
                      detections={mapMode === 'raw' ? visibleRawDetections : undefined}
                      events={filtered}
                      selected={selected}
                      onSelect={choose}
                      hazards={hazards}
                      showHazards={showHazards && mapMode === 'events'}
                      showIndustrial={showIndustrial && mapMode === 'events'}
                      subscriberLocation={subscriberLocation}
                      showSubscriberRadius={showSubscriberRadius && mapMode === 'events'}
                    />

                    {/* Floating Layer Controls Panel */}
                    <div className="map-floating-layer-panel">
                      <span className="layer-panel-title">MAP LAYERS</span>
                      <label className="floating-layer-toggle">
                        <input
                          type="checkbox"
                          checked={showHazards}
                          disabled={mapMode !== 'events'}
                          onChange={(e) => setShowHazards(e.target.checked)}
                        />
                        <span>NASA EONET Hazards</span>
                      </label>
                      <label className="floating-layer-toggle">
                        <input
                          type="checkbox"
                          checked={showIndustrial}
                          disabled={mapMode !== 'events'}
                          onChange={(e) => setShowIndustrial(e.target.checked)}
                        />
                        <span>OSM Industrial Footprints</span>
                      </label>
                      {(notif?.latitude != null && notif?.longitude != null) && (
                        <label className="floating-layer-toggle">
                          <input
                            type="checkbox"
                            checked={showSubscriberRadius}
                            disabled={mapMode !== 'events'}
                            onChange={(e) => setShowSubscriberRadius(e.target.checked)}
                          />
                          <span>Alert Coverage Radius</span>
                        </label>
                      )}
                    </div>

                    {/* Floating Map Legend */}
                    <div className="map-floating-legend">
                      {mapMode === 'raw' ? (
                        <span>Raw FIRMS: Cyan VIIRS (375m) · Purple MODIS (1km)</span>
                      ) : (
                        <>
                          <span className="legend-item"><i className="legend-dot critical" /> Critical</span>
                          <span className="legend-item"><i className="legend-dot high" /> High</span>
                          <span className="legend-item"><i className="legend-dot medium" /> Medium</span>
                          <span className="legend-item"><i className="legend-dot normal" /> Normal</span>
                          {showHazards && <span className="legend-item"><i className="legend-dot hazard" /> EONET hazard</span>}
                          {showIndustrial && <span className="legend-item"><i className="legend-dot industrial" /> OSM industrial</span>}
                        </>
                      )}
                    </div>
                  </div>

                  <aside className="map-event-feed">
                    <div className="map-event-feed-head">
                      <h3>Monitored Events</h3>
                      <span className="badge normal">{filtered.length}</span>
                    </div>
                    {filtered.slice(0, 30).map((e) => (
                      <button
                        key={e.id}
                        type="button"
                        className={`event-feed-card ${selected?.id === e.id ? 'selected' : ''}`}
                        onClick={() => choose(e)}
                      >
                        <div className="event-feed-top">
                          <span className="event-feed-id">{e.is_demo ? 'DEMO · ' : ''}{e.id.slice(0, 18)}</span>
                          <RiskBadge level={e.risk?.risk_level} />
                        </div>
                        <div className="event-feed-class">
                          <span>{label(e.classification?.predicted_class)}</span>
                          <ChevronRight size={14} className="text-muted" />
                        </div>
                        <div className="event-feed-location">
                          {e.context?.location?.display_name || `${num(e.latitude, 3)}° N, ${num(e.longitude, 3)}° E`}
                        </div>
                      </button>
                    ))}
                  </aside>
                </div>
              </section>
            </>
          )}

          {/* VIEW: Events Explorer */}
          {view === 'Events' && (
            <>
              <FilterToolbar
                reviewFilter={reviewFilter}
                setReviewFilter={setReviewFilter}
                classification={classificationFilter}
                setClassification={setClassificationFilter}
                classifications={[...new Set(events.map(e=>e.classification?.predicted_class || 'unclassified'))].sort()}
                search={search}
                setSearch={setSearch}
                filter={filter}
                setFilter={setFilter}
                sourceFilter={sourceFilter}
                setSourceFilter={setSourceFilter}
                dateFilter={dateFilter}
                setDateFilter={setDateFilter}
                contextFilter={contextFilter}
                setContextFilter={setContextFilter}
                areaQuery={areaQuery}
                setAreaQuery={setAreaQuery}
                areas={areas}
                area={area}
                setArea={setArea}
                findArea={findArea}
                busy={busy}
                totalCount={events.length}
                filteredCount={filtered.length}
              />

              <EventTable
                events={filtered}
                selectedId={selected?.id}
                onSelect={choose}
                busy={busy}
              />
            </>
          )}

          {/* VIEW: Alerts */}
          {view === 'Alerts' && (
            <AlertCenter
              alerts={alerts}
              onAcknowledge={acknowledge}
              ackBusy={ackBusy}
              onSelectEvent={(eventId) => {
                const target = events.find((e) => e.id === eventId);
                if (target) choose(target);
                else setError(`Event ${eventId} not found in active scope.`);
              }}
              busy={busy}
            />
          )}

          {/* VIEW: Analytics */}
          {view === 'Analytics' && (
            <AnalyticsView
              alerts={alerts}
              providers={providerHealth}
              reviewedCount={reviewReadiness?.reviewed_rows}
              trends={trends}
              trendsAvailable={trendsAvailable}
              trendsReason={trendsReason}
              trendsBusy={trendsBusy}
              days={days}
              setDays={setDays}
              events={events}
              demo={demo}
            />
          )}

          {/* VIEW: AI Copilot */}
          {view === 'AI Copilot' && (
            <div className="analytics-view-container">
              <section className="settings-panel">
                <div className="settings-panel-header">
                  <div className="settings-icon-wrap" style={{ background: '#ede9fe', color: '#6d28d9' }}>
                    <Sparkles size={22} />
                  </div>
                  <div>
                    <h2>ThermaGuard AI Evidence Copilot</h2>
                    <p className="text-muted">
                      Operational AI explanations grounded strictly in verified event data, weather grids, and satellite observations.
                    </p>
                  </div>
                </div>

                <div className="copilot-conversation-area" style={{ maxHeight: '480px' }}>
                  {chatBusy ? (
                    <div className="copilot-busy-state">
                      <Sparkles size={24} className="spin text-teal" />
                      <p>Querying verified event evidence from system repository…</p>
                    </div>
                  ) : answer ? (
                    <div className="copilot-answer-rendered">
                      <div className="copilot-answer-bubble">{answer}</div>
                    </div>
                  ) : (
                    <div className="copilot-placeholder-state">
                      <Sparkles size={36} className="text-muted" />
                      <p>
                        Select one event from the map or event explorer before asking a question.
                      </p>
                    </div>
                  )}
                </div>

                <form className="copilot-input-form" onSubmit={ask} style={{ borderRadius: '8px' }}>
                  <input
                    type="text"
                    aria-label="Copilot question"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder={
                      selected
                        ? `Ask about event ${selected.id.slice(0, 10)}…`
                        : 'Select an event from Events first…'
                    }
                    required
                    maxLength={1000}
                    disabled={chatBusy}
                  />
                  <button
                    type="submit"
                    className="primary"
                    disabled={chatBusy || !question.trim() || !selected}
                  >
                    <Send size={16} />
                    Submit
                  </button>
                </form>
              </section>
            </div>
          )}

          {/* VIEW: Providers */}
          {view === 'Providers' && (
            <ProviderHealthGrid
              providerHealth={providerHealth}
              isAdmin={user.role === 'admin'}
              demo={demo}
              syncBusy={syncBusy}
              onSyncFirms={syncFirms}
            />
          )}

          {/* VIEW: Review & Labels */}
          {view === 'Review & Labels' && (
            <ReviewCenter
              readiness={reviewReadiness}
              candidates={reviewCandidates}
              model={model}
              isAdmin={user.role === 'admin'}
              trainBusy={trainBusy}
              onTrainModel={trainModel}
            />
          )}

          {/* VIEW: Settings */}
          {view === 'Settings' && (
            <><section className="review-card"><h2>Profile &amp; display</h2><p>{user.email} · {user.role}</p><label><input type="checkbox" checked={compactDisplay} onChange={e=>setCompactDisplay(e.target.checked)}/>Compact display</label><p>Provider configuration is managed on the server. <button className="button" onClick={()=>setView('Providers')}>View provider status</button></p><p>Device registration: not exposed by the backend status API. Firebase: {providerHealth?.providers.firebase?.status || 'Unavailable'}.</p></section><NotificationSettings
              authToken={token}
              notif={notif}
              notifBusy={notifBusy}
              onSaveNotif={saveNotif}
              isAdmin={user.role === 'admin'}
              organizations={organizations}
              assignments={assignments}
              onCreateOrg={async (values) => {
                await apiPost('/admin/organizations', values, token);
                setNotice('Organization created successfully.');
                const orgs = await apiGet<Organization[]>('/admin/organizations', token);
                setOrganizations(orgs);
              }}
              onAssignArea={async (values) => {
                await apiPost(
                  '/admin/assignments',
                  {
                    ...values,
                    organization_id: Number(values.organization_id),
                    bounds: values.bounds.split(',').map(Number),
                  },
                  token
                );
                setNotice('Territory assigned successfully.');
                const assigns = await apiGet<Assignment[]>('/admin/assignments', token);
                setAssignments(assigns);
              }}
              onUpdateThreshold={async (threshold) => {
                await apiPost('/admin/threshold', { threshold }, token);
                setNotice(`Global risk threshold updated to ${threshold}.`);
                await refresh();
              }}
              onAssignUser={async (values) => {
                await apiPost(
                  '/admin/users/assign',
                  { email: values.email, organization_id: Number(values.organization_id) },
                  token
                );
                setNotice('User assigned to organization.');
              }}
            /></>
          )}

          {/* Footer */}
          <footer className="footer">
            <span>ThermaGuard AI · Operational Thermal Intelligence</span>
            <div className="footer-steps">
              <span>DETECT</span>
              <ChevronRight size={10} />
              <span>UNDERSTAND</span>
              <ChevronRight size={10} />
              <span>CLASSIFY</span>
              <ChevronRight size={10} />
              <span>ASSESS RISK</span>
              <ChevronRight size={10} />
              <span>ACT</span>
            </div>
            <small>Evidence before action.</small>
          </footer>
        </main>
      </div>

      {/* Selected Event Detail Drawer */}
      {selected && detailOpen && (
        <EventDetailDrawer
          event={selected}
          onClose={() => setDetailOpen(false)}
          onZoom={() => {setView('Live Map');setDetailOpen(false)}}
          token={token}
          evidence={evidence}
          evidenceBusy={evidenceBusy}
          history={history}
          onOpenCopilot={() => {
            setCopilot(true);
          }}
          onUpdateEventContext={updateSelectedEventContext}
        />
      )}

      {/* Copilot Dialog */}
      <CopilotModal
        isOpen={copilot}
        onClose={() => setCopilot(false)}
        selected={selected}
        question={question}
        setQuestion={setQuestion}
        answer={answer}
        chatMode={chatMode}
        chatBusy={chatBusy}
        onAsk={ask}
        onSelectSuggestedQuestion={(q) => {
          setQuestion(q);
        }}
      />
    </div>
  );
}
