import { useEffect, useState, useRef, type ReactNode, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminApi, clearToken, isAdminLoggedIn, exportToCsv, type ComprehensiveMetrics, type HealthInfo } from '../services/api/adminClient';
import {
  LayoutDashboard, Users, ClipboardList, RefreshCcw, Activity, AlertTriangle,
  Pill, Heart, Bell, Shield, LogOut, Search, Headphones, Play,
  ChevronRight, ChevronLeft, Weight, Footprints, Timer, TrendingUp, Send, Database,
  Download, X, Info, BarChart3, Brain,
  type LucideIcon,
} from 'lucide-react';

type TabId = 'overview' | 'users' | 'assessments' | 'followups' | 'prescriptions' | 'activity' | 'sugar' | 'notifications' | 'safety' | 'audio' | 'backend';

interface TabDef {
  id: TabId;
  label: string;
  icon: LucideIcon;
}

const TABS: TabDef[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'users', label: 'Users', icon: Users },
  { id: 'assessments', label: 'Assessments', icon: ClipboardList },
  { id: 'followups', label: 'Follow-ups', icon: RefreshCcw },
  { id: 'prescriptions', label: 'Rx & Risk', icon: Pill },
  { id: 'activity', label: 'Activity', icon: Footprints },
  { id: 'sugar', label: 'Health Data', icon: Heart },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'safety', label: 'Safety', icon: Shield },
  { id: 'audio', label: 'Audio Assets', icon: Headphones },
  { id: 'backend', label: 'Backend', icon: Database },
];

function MetricCard({ icon: Icon, value, label, sub, color }: { icon: LucideIcon; value: string | number; label: string; sub?: string; color?: string }) {
  return (
    <div className="admin-mcard" style={color ? { borderLeftColor: color } : undefined}>
      <Icon size={22} style={{ color: color || 'var(--admin-accent)' }} />
      <div>
        <span className="admin-mcard-value">{value}</span>
        <span className="admin-mcard-label">{label}</span>
        {sub && <span className="admin-mcard-sub">{sub}</span>}
      </div>
    </div>
  );
}

function Bar({ value, max, label, color }: { value: number; max: number; label: string; color?: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="admin-bar-row">
      <span className="admin-bar-label">{label}</span>
      <div className="admin-bar-track">
        <div className="admin-bar-fill" style={{ width: `${pct}%`, background: color || 'var(--admin-accent)' }} />
      </div>
      <span className="admin-bar-value">{value}</span>
    </div>
  );
}

function SectionCard({ title, children, icon: Icon }: { title: string; children: ReactNode; icon?: LucideIcon }) {
  return (
    <div className="admin-scard">
      <h3 className="admin-scard-title">{Icon && <Icon size={18} />}{title}</h3>
      {children}
    </div>
  );
}

function fmt(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return String(num);
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<ComprehensiveMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [days, setDays] = useState(30);

  // ── User list state ──
  const [usersList, setUsersList] = useState<any[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersPage, setUsersPage] = useState(1);
  const [usersLimit, setUsersLimit] = useState(10);
  const [usersTotalPages, setUsersTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── User drill-down modal ──
  const [detailUser, setDetailUser] = useState<any>(null);
  const [detailData, setDetailData] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // ── Audio section state ──
  const [audioMissing, setAudioMissing] = useState(0);
  const [audioMissingList, setAudioMissingList] = useState<any[]>([]);
  const [audioGenerating, setAudioGenerating] = useState(false);
  const [audioMsg, setAudioMsg] = useState('');

  // ── Broadcast state ──
  const [broadcasting, setBroadcasting] = useState<string | null>(null);
  const [broadcastResult, setBroadcastResult] = useState<string>('');

  // ── Health state ──
  const [healthInfo, setHealthInfo] = useState<HealthInfo | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  // ── Temporary audio cleanup state ──
  const [cleanupRunning, setCleanupRunning] = useState(false);
  const [cleanupResult, setCleanupResult] = useState('');

  // ── Weekly adherence page for the table ──
  const [adhPage, setAdhPage] = useState(0);
  const [adhPageSize, setAdhPageSize] = useState(20);

  // ── Per-user assessment sessions pagination ──
  const [assessPage, setAssessPage] = useState(0);
  const [assessPageSize, setAssessPageSize] = useState(10);

  // ── Per-user follow-up sessions pagination ──
  const [fuPage, setFuPage] = useState(0);
  const [fuPageSize, setFuPageSize] = useState(10);

  useEffect(() => {
    if (!isAdminLoggedIn()) { navigate('/admin'); return; }
    loadAll();
  }, []);

  useEffect(() => {
    loadUsers();
  }, [usersPage, usersLimit]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [m] = await Promise.all([adminApi.getComprehensiveMetrics(days)]);
      setMetrics(m);
      await loadUsers();
    } catch {
      clearToken();
      navigate('/admin');
    }
    setLoading(false);
  };

  const loadAllWithDays = (d: number) => {
    setDays(d);
    setLoading(true);
    adminApi.getComprehensiveMetrics(d).then(m => {
      setMetrics(m);
      setLoading(false);
    }).catch(() => {
      clearToken();
      navigate('/admin');
    });
  };

  const loadUsers = async () => {
    try {
      const r = await adminApi.getUsers({ search, page: usersPage, limit: usersLimit });
      setUsersList(r.users);
      setUsersTotal(r.total);
      setUsersTotalPages(r.totalPages);
    } catch {
      clearToken();
      navigate('/admin');
    }
  };

  const handleSearchChange = (e: ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setSearch(v);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      setUsersPage(1);
      loadUsers();
    }, 400);
  };

  const checkMissingAudio = async () => {
    try {
      const r = await adminApi.getMissingAudio();
      setAudioMissing(r.total);
      setAudioMissingList(r.missing);
    } catch { /* ignore */ }
  };

  const handleBroadcast = async (type: 'follow_up' | 'exercise_reminder' | 'sugar_test') => {
    if (broadcasting) return;
    setBroadcasting(type);
    setBroadcastResult('');
    try {
      const r = await adminApi.broadcastNotification(type);
      setBroadcastResult(`✅ Sent to ${r.sent} users (${r.failed} failed, ${r.totalUsersWithSubscriptions} subscribed)`);
    } catch (e: any) {
      setBroadcastResult(`❌ ${e.message}`);
    }
    setBroadcasting(null);
  };

  const handleGenerateAudio = async () => {
    if (audioGenerating) return;
    setAudioGenerating(true);
    setAudioMsg('Generating...');
    try {
      const r = await adminApi.generateAudio();
      setAudioMsg(`Generated: ${r.generated}, Skipped: ${r.skipped}, Failed: ${r.failed}`);
      await checkMissingAudio();
    } catch (e: any) {
      setAudioMsg(`Error: ${e.message}`);
    }
    setAudioGenerating(false);
  };

  const handleUserClick = async (userId: string) => {
    setDetailLoading(true);
    setDetailData(null);
    try {
      const data = await adminApi.getUserDetail(userId);
      setDetailData(data);
      setDetailUser(data.user);
    } catch { /* ignore */ }
    setDetailLoading(false);
  };

  const loadHealth = async () => {
    setHealthLoading(true);
    try {
      const h = await adminApi.getHealth();
      setHealthInfo(h);
    } catch { /* ignore */ }
    setHealthLoading(false);
  };

  useEffect(() => { if (activeTab === 'audio') checkMissingAudio(); }, [activeTab]);
  useEffect(() => { if (activeTab === 'backend') loadHealth(); }, [activeTab]);

  const handleLogout = () => { clearToken(); navigate('/admin'); };

  const PAGE_SIZES = [10, 20, 50, 100];

  // ── Export helpers ──
  const exportUsers = () => {
    if (!usersList.length) return;
    exportToCsv(usersList.map(u => ({
      displayUserId: u.displayUserId,
      name: `${u.firstName} ${u.lastName}`,
      language: u.preferredLanguage,
      assessmentsCount: u.assessmentsCount,
      currentPlan: u.currentPlan,
      followUpsDue: u.followUpsDue,
    })), 'users.csv');
  };

  const exportDropOff = () => {
    if (!metrics) return;
    exportToCsv(metrics.assessments.dropOffByQuestion.map(q => ({
      moduleId: q.moduleId,
      questionId: q.questionId,
      responseCount: q.responseCount,
      funnelPercent: q.funnelPercent,
      dropFromFirst: q.dropFromFirst,
    })), 'dropoff.csv');
  };

  if (loading || !metrics) {
    return (
      <div className="admin-loading">
        <div className="admin-spinner" />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  const m = metrics;

  // ── Renderers ──
  const renderOverview = () => (
    <div className="admin-tab-content">
      <div className="admin-tab-header-row">
        <h2 className="admin-tab-title"><LayoutDashboard size={22} /> Overview</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <label style={{ fontSize: 13, color: 'var(--admin-text-sec)' }}>Active window:</label>
          <select className="admin-page-size-select" value={days}
            onChange={e => loadAllWithDays(Number(e.target.value))}>
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
          </select>
        </div>
      </div>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={Users} value={fmt(m.userOverview.totalUsers)} label="Total Users" />
        <MetricCard icon={Activity} value={fmt(m.userOverview.activeToday)} label="Active Today" />
        <MetricCard icon={Activity} value={fmt(m.userOverview.activeThisWeek)} label="Active This Week" />
        <MetricCard icon={Activity} value={fmt(m.userOverview.activeThisMonth)} label={`Active (${days}d)`} />
      </div>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={ClipboardList} value={fmt(m.assessments.totalSessions)} label="Total Assessments" />
        <MetricCard icon={ClipboardList} value={`${m.assessments.firstAssessmentCompletionRate}%`} label="Assessment Completion" sub={`${m.assessments.completed} completed / ${m.assessments.completed + m.assessments.abandoned} finished`} />
        <MetricCard icon={RefreshCcw} value={fmt(m.followUps.totalSessions)} label="Follow-up Sessions" />
        <MetricCard icon={TrendingUp} value={`${m.followUps.completionRate}%`} label="Follow-up Completion" sub={`${m.followUps.completed} completed`} />
      </div>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={Footprints} value={m.activity.avgMinutesCompleted} label="Avg Activity Min" sub={`Prescribed: ${m.activity.avgPrescribedMinutesPerWeek}/wk`} />
        <MetricCard icon={TrendingUp} value={`${m.activity.exerciseAdherenceRate}%`} label="Exercise Adherence" />
        <MetricCard icon={Bell} value={fmt(m.notifications.pushSent)} label="Notifications Sent" />
        <MetricCard icon={AlertTriangle} value={fmt(m.safety.activitySafetyFlags + m.safety.followUpSafetyFlags)} label="Safety Flags" color="#EF4444" />
      </div>

      <div className="admin-scard-row">
        <SectionCard title="Language Distribution" icon={Users}>
          {m.userOverview.languageDistribution.map(l => (
            <Bar key={l.language} label={l.language === 'ta' ? 'Tamil' : 'English'} value={l.count}
              max={m.userOverview.totalUsers} />
          ))}
        </SectionCard>
        <SectionCard title="Streak Averages" icon={Timer}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '8px 0' }}>
            <div><span className="admin-stat-label">Avg Login Streak (max per user)</span><span className="admin-stat-value">{m.userOverview.avgLoginStreakWeeks} weeks</span></div>
            <div><span className="admin-stat-label">Max Login Streak</span><span className="admin-stat-value">{m.userOverview.maxLoginStreakWeeks} weeks</span></div>
            <div><span className="admin-stat-label">Avg Adherence Streak (max per user)</span><span className="admin-stat-value">{m.userOverview.avgAdherenceStreakWeeks} weeks</span></div>
            <div><span className="admin-stat-label">Max Adherence Streak</span><span className="admin-stat-value">{m.userOverview.maxAdherenceStreakWeeks} weeks</span></div>
          </div>
        </SectionCard>
      </div>
    </div>
  );

  const renderUsers = () => (
    <div className="admin-tab-content">
      <div className="admin-tab-header-row">
        <h2 className="admin-tab-title"><Users size={22} /> Users</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button className="admin-action-btn" onClick={exportUsers} title="Export to CSV"><Download size={14} /> Export</button>
          <div className="admin-search-wrapper">
            <Search size={16} />
            <input type="text" placeholder="Search..." value={search}
              onChange={handleSearchChange} className="admin-search-input" />
          </div>
        </div>
      </div>

      <div className="admin-mcard-grid-3" style={{ marginBottom: 16 }}>
        <MetricCard icon={Users} value={fmt(usersTotal)} label="Registered" />
        <MetricCard icon={Activity} value={fmt(m.userOverview.activeThisMonth)} label={`Active (${days}d)`} />
        <MetricCard icon={TrendingUp} value={`${m.userOverview.avgLoginStreakWeeks}w`} label="Avg Login Streak" />
      </div>

      <div className="admin-tab-header-row" style={{ justifyContent: 'flex-end', gap: 12, marginBottom: 8 }}>
        <span className="admin-pagination-info">
          {usersTotal > 0 ? `Page ${usersPage} of ${usersTotalPages} (${usersTotal} users)` : 'No users'}
        </span>
        <select className="admin-page-size-select" value={usersLimit}
          onChange={e => { setUsersLimit(Number(e.target.value)); setUsersPage(1); }}>
          {PAGE_SIZES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <div className="admin-pagination-btns">
          <button className="admin-page-btn" disabled={usersPage <= 1}
            onClick={() => setUsersPage(p => Math.max(1, p - 1))}>
            <ChevronLeft size={16} />
          </button>
          <button className="admin-page-btn" disabled={usersPage >= usersTotalPages}
            onClick={() => setUsersPage(p => p + 1)}>
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>User ID</th>
              <th>Name</th>
              <th>Lang</th>
              <th>Sessions</th>
              <th>Plan</th>
              <th>Login Streak</th>
              <th>Adhere Streak</th>
              <th>Follow-ups Due</th>
            </tr>
          </thead>
          <tbody>
            {usersList.map(u => {
              const ls = m.userOverview.perUserLoginStreaks.find(s => s.displayUserId === u.displayUserId);
              const as = m.userOverview.perUserAdherenceStreaks.find(s => s.displayUserId === u.displayUserId);
              return (
                <tr key={u.id} className="admin-clickable-row" onClick={() => { setDetailUser(u); handleUserClick(u.id); }}>
                  <td className="admin-cell-mono">{u.displayUserId}</td>
                  <td>{u.firstName} {u.lastName}</td>
                  <td>{u.preferredLanguage === 'ta' ? 'தமிழ்' : 'EN'}</td>
                  <td>{u.assessmentsCount}</td>
                  <td><span className={`admin-plan-badge ${u.currentPlan}`}>{u.currentPlan === 'medical_clearance' ? 'MedClr' : u.currentPlan}</span></td>
                  <td>{ls?.streakWeeks || 0}w</td>
                  <td>{as?.streakWeeks || 0}w</td>
                  <td>{u.followUpsDue}</td>
                </tr>
              );
            })}
            {usersList.length === 0 && <tr><td colSpan={8} className="admin-empty">No users found</td></tr>}
          </tbody>
        </table>
      </div>

      <SectionCard title="Top Login Streaks" icon={Timer}>
        {m.userOverview.perUserLoginStreaks.slice(0, 10).map(s => (
          <Bar key={s.displayUserId} label={`${s.name} (${s.displayUserId})`} value={s.streakWeeks}
            max={m.userOverview.maxLoginStreakWeeks} />
        ))}
      </SectionCard>

      {/* User Detail Modal */}
      {detailUser && (
        <div className="admin-modal-overlay" onClick={() => { setDetailUser(null); setDetailData(null); }}>
          <div className="admin-modal" onClick={e => e.stopPropagation()}>
            <div className="admin-modal-header">
              <h3><Users size={18} /> {detailUser.firstName} {detailUser.lastName}</h3>
              <button className="admin-modal-close" onClick={() => { setDetailUser(null); setDetailData(null); }}><X size={18} /></button>
            </div>
            {detailLoading ? (
              <div className="admin-loading" style={{ padding: 40 }}><div className="admin-spinner" /></div>
            ) : detailData ? (
              <div className="admin-modal-body">
                <SectionCard title="User Info" icon={Users}>
                  <div><span className="admin-stat-label">ID</span><span className="admin-stat-value">{detailData.user.displayUserId}</span></div>
                  <div><span className="admin-stat-label">Language</span><span className="admin-stat-value">{detailData.user.preferredLanguage}</span></div>
                  <div><span className="admin-stat-label">Role</span><span className="admin-stat-value">{detailData.user.role}</span></div>
                  <div><span className="admin-stat-label">Created</span><span className="admin-stat-value">{new Date(detailData.user.createdAt).toLocaleDateString()}</span></div>
                </SectionCard>
                {detailData.assessments.length > 0 && (
                  <SectionCard title={`Assessments (${detailData.assessments.length})`} icon={ClipboardList}>
                    {detailData.assessments.slice(0, 10).map((a: any) => (
                      <div key={a.id} className="admin-detail-row">
                        <span>{a.status}</span>
                        <span>{new Date(a.startedAt).toLocaleDateString()}</span>
                      </div>
                    ))}
                  </SectionCard>
                )}
                {detailData.prescriptions.length > 0 && (
                  <SectionCard title={`Prescriptions (${detailData.prescriptions.length})`} icon={Pill}>
                    {detailData.prescriptions.slice(0, 5).map((p: any) => (
                      <div key={p.id} className="admin-detail-row">
                        <span>{p.planType}</span>
                        <span>{new Date(p.createdAt).toLocaleDateString()}</span>
                      </div>
                    ))}
                  </SectionCard>
                )}
                {detailData.sugarReadings.length > 0 && (
                  <SectionCard title={`Sugar Readings (${detailData.sugarReadings.length})`} icon={Heart}>
                    <div className="admin-table-wrapper">
                      <table className="admin-table">
                        <thead><tr><th>Type</th><th>Value</th><th>Date</th></tr></thead>
                        <tbody>
                          {detailData.sugarReadings.slice(0, 10).map((r: any) => (
                            <tr key={r.id}><td>{r.readingType}</td><td>{r.value}</td><td>{new Date(r.recordedAt).toLocaleDateString()}</td></tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </SectionCard>
                )}
                {detailData.activityLogs.length > 0 && (
                  <SectionCard title={`Activity Logs (${detailData.activityLogs.length})`} icon={Footprints}>
                    <div className="admin-table-wrapper">
                      <table className="admin-table">
                        <thead><tr><th>Date</th><th>Min</th><th>Strength</th><th>Safety</th></tr></thead>
                        <tbody>
                          {detailData.activityLogs.slice(0, 10).map((l: any) => (
                            <tr key={l.id}><td>{new Date(l.activityDate).toLocaleDateString()}</td><td>{l.completedMinutes}</td><td>{l.strengthCompleted ? '✓' : '✗'}</td><td>{l.safetyFlag ? '⚠' : ''}</td></tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </SectionCard>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );

  const renderAssessments = () => (
    <div className="admin-tab-content">
      <h2 className="admin-tab-title"><ClipboardList size={22} /> Assessments</h2>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={ClipboardList} value={fmt(m.assessments.totalSessions)} label="Total Sessions" />
        <MetricCard icon={ClipboardList} value={fmt(m.assessments.completed)} label="Completed" />
        <MetricCard icon={ClipboardList} value={fmt(m.assessments.abandoned)} label="Abandoned" color="#F59E0B" />
        <MetricCard icon={ClipboardList} value={fmt(m.assessments.inProgress)} label="In Progress" color="#3B82F6" />
      </div>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={TrendingUp} value={`${m.assessments.firstAssessmentCompletionRate}%`} label="Completion Rate" sub="excludes in-progress" />
        <MetricCard icon={Timer} value={`${m.assessments.avgCompletionTimeMinutes}m`} label="Avg Time to Complete" />
      </div>

      <SectionCard title="Per-User Assessment Sessions" icon={Users}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span className="admin-pagination-info">
            Showing {assessPage * assessPageSize + 1}–{Math.min((assessPage + 1) * assessPageSize, m.assessments.perUserSessions.length)} of {m.assessments.perUserSessions.length}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <select className="admin-page-size-select" value={assessPageSize}
              onChange={e => { setAssessPageSize(Number(e.target.value)); setAssessPage(0); }}>
              {PAGE_SIZES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <div className="admin-pagination-btns">
              <button className="admin-page-btn" disabled={assessPage <= 0} onClick={() => setAssessPage(p => p - 1)}><ChevronLeft size={16} /></button>
              <button className="admin-page-btn" disabled={(assessPage + 1) * assessPageSize >= m.assessments.perUserSessions.length} onClick={() => setAssessPage(p => p + 1)}><ChevronRight size={16} /></button>
            </div>
          </div>
        </div>
        {m.assessments.perUserSessions.slice(assessPage * assessPageSize, (assessPage + 1) * assessPageSize).map(s => (
          <Bar key={s.userId} label={`${s.name} (${s.displayUserId})`} value={s.count}
            max={Math.max(...m.assessments.perUserSessions.map(x => x.count), 1)} />
        ))}
      </SectionCard>

      <SectionCard title="Drop-off Funnel by Question" icon={Brain}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <button className="admin-action-btn" onClick={exportDropOff}><Download size={14} /> Export CSV</button>
        </div>
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr><th>Module</th><th>Question</th><th>Responses</th><th>Funnel %</th><th>Drop from First</th></tr>
            </thead>
            <tbody>
              {m.assessments.dropOffByQuestion.map(q => (
                <tr key={q.questionId}>
                  <td className="admin-cell-mono">{q.moduleId}</td>
                  <td className="admin-cell-mono">{q.questionId}</td>
                  <td>{q.responseCount}</td>
                  <td>
                    <div className="admin-bar-row" style={{ minWidth: 120 }}>
                      <div className="admin-bar-track" style={{ height: 12 }}>
                        <div className="admin-bar-fill" style={{ width: `${q.funnelPercent}%`, background: q.funnelPercent > 50 ? 'var(--admin-accent)' : '#EF4444' }} />
                      </div>
                      <span className="admin-bar-value" style={{ fontSize: 12 }}>{q.funnelPercent}%</span>
                    </div>
                  </td>
                  <td style={{ color: q.dropFromFirst > 20 ? '#EF4444' : 'inherit' }}>{q.dropFromFirst}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );

  const renderFollowUps = () => (
    <div className="admin-tab-content">
      <h2 className="admin-tab-title"><RefreshCcw size={22} /> Follow-ups</h2>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={RefreshCcw} value={fmt(m.followUps.totalSessions)} label="Total" />
        <MetricCard icon={RefreshCcw} value={fmt(m.followUps.due)} label="Due" color="#3B82F6" />
        <MetricCard icon={RefreshCcw} value={fmt(m.followUps.completed)} label="Completed" />
        <MetricCard icon={AlertTriangle} value={fmt(m.followUps.missed)} label="Missed" color="#F59E0B" />
      </div>
      <div className="admin-mcard-grid-4">
        <MetricCard icon={AlertTriangle} value={fmt(m.followUps.overdue)} label="Overdue" color="#EF4444" />
        <MetricCard icon={TrendingUp} value={`${m.followUps.completionRate}%`} label="Completion Rate" />
      </div>

      <SectionCard title="Per-User Follow-up Sessions" icon={Users}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span className="admin-pagination-info">
            Showing {fuPage * fuPageSize + 1}–{Math.min((fuPage + 1) * fuPageSize, m.followUps.perUserSessions.length)} of {m.followUps.perUserSessions.length}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <select className="admin-page-size-select" value={fuPageSize}
              onChange={e => { setFuPageSize(Number(e.target.value)); setFuPage(0); }}>
              {PAGE_SIZES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <div className="admin-pagination-btns">
              <button className="admin-page-btn" disabled={fuPage <= 0} onClick={() => setFuPage(p => p - 1)}><ChevronLeft size={16} /></button>
              <button className="admin-page-btn" disabled={(fuPage + 1) * fuPageSize >= m.followUps.perUserSessions.length} onClick={() => setFuPage(p => p + 1)}><ChevronRight size={16} /></button>
            </div>
          </div>
        </div>
        {m.followUps.perUserSessions.slice(fuPage * fuPageSize, (fuPage + 1) * fuPageSize).map(s => (
          <Bar key={s.displayUserId} label={`${s.name} (${s.displayUserId})`}
            value={s.total} max={Math.max(...m.followUps.perUserSessions.map(x => x.total), 1)} />
        ))}
      </SectionCard>
    </div>
  );

  const renderPrescriptions = () => (
    <div className="admin-tab-content">
      <h2 className="admin-tab-title"><Pill size={22} /> Prescription Plans & Risk</h2>

      <div className="admin-scard-row">
        <SectionCard title="Plan Distribution" icon={Pill}>
          {m.prescriptions.planDistribution.map(p => (
            <Bar key={p.planType} label={p.planType.replace(/_/g, ' ')}
              value={p.count} max={Math.max(...m.prescriptions.planDistribution.map(x => x.count), 1)} />
          ))}
        </SectionCard>

        <SectionCard title="Overall Risk" icon={AlertTriangle}>
          {m.prescriptions.overallRisk.map(r => (
            <Bar key={r.category} label={r.category}
              value={r.count} max={Math.max(...m.prescriptions.overallRisk.map(x => x.count), 1)}
              color={r.category === 'high' ? '#EF4444' : r.category === 'moderate' ? '#F59E0B' : '#4A9D6E'} />
          ))}
        </SectionCard>
      </div>

      <div className="admin-scard-row">
        <SectionCard title="Glycemic Risk" icon={Activity}>
          {m.prescriptions.glycemicRisk.map(r => (
            <Bar key={r.category} label={r.category}
              value={r.count} max={Math.max(...m.prescriptions.glycemicRisk.map(x => x.count), 1)} />
          ))}
        </SectionCard>
        <SectionCard title="Physical Activity Risk" icon={Footprints}>
          {m.prescriptions.physicalActivityRisk.map(r => (
            <Bar key={r.category} label={r.category}
              value={r.count} max={Math.max(...m.prescriptions.physicalActivityRisk.map(x => x.count), 1)} />
          ))}
        </SectionCard>
      </div>

      <div className="admin-scard-row">
        <SectionCard title="Sedentary Risk" icon={Timer}>
          {m.prescriptions.sedentaryRisk.map(r => (
            <Bar key={r.category} label={r.category}
              value={r.count} max={Math.max(...m.prescriptions.sedentaryRisk.map(x => x.count), 1)} />
          ))}
        </SectionCard>

        <SectionCard title="BMI Distribution" icon={Weight}>
          {m.prescriptions.bmiDistribution.map(r => (
            <Bar key={r.category} label={r.category}
              value={r.count} max={Math.max(...m.prescriptions.bmiDistribution.map(x => x.count), 1)} />
          ))}
        </SectionCard>
      </div>

      <div className="admin-scard-row">
        <SectionCard title="Complication Flags" icon={AlertTriangle}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '8px 0' }}>
            <div><span className="admin-stat-label">PAR-Q Clearance Required</span><span className="admin-stat-value">{m.prescriptions.parQClearanceRequired}</span></div>
            <div><span className="admin-stat-label">Users with Complications</span><span className="admin-stat-value">{m.prescriptions.complicationFlags.totalUsersWithFlags}</span></div>
            {Object.entries(m.prescriptions.complicationFlags.breakdown).map(([k, v]) => (
              <div key={k}><span className="admin-stat-label">{k.replace(/_/g, ' ')}</span><span className="admin-stat-value">{v}</span></div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  );

  const renderActivity = () => (
    <div className="admin-tab-content">
      <h2 className="admin-tab-title"><Footprints size={22} /> Activity & Adherence</h2>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={Footprints} value={m.activity.avgMinutesCompleted} label="Avg Min / Session" />
        <MetricCard icon={Footprints} value={m.activity.avgDaysCompleted} label="Avg Days / Session" />
        <MetricCard icon={TrendingUp} value={`${m.activity.exerciseAdherenceRate}%`} label="Exercise Adherence" />
        <MetricCard icon={Timer} value={`${m.activity.avgPrescribedMinutesPerWeek}/wk`} label="Avg Prescribed" />
      </div>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={Footprints} value={`${m.activity.strengthAdherence.rate}%`} label="Strength Adherence"
          sub={`${m.activity.strengthAdherence.completedSessions}/${m.activity.strengthAdherence.totalLogs} sessions`} />
        <MetricCard icon={TrendingUp} value={`${m.userOverview.avgAdherenceStreakWeeks}w`} label="Avg Adherence Streak" />
      </div>

      <SectionCard title="Completed vs Prescribed (Weekly Minutes)" icon={Activity}>
        <Bar label="Prescribed" value={m.activity.avgCompletedVsPrescribed.prescribedMinutes}
          max={Math.max(m.activity.avgCompletedVsPrescribed.prescribedMinutes, 1)} />
        <Bar label="Completed" value={m.activity.avgCompletedVsPrescribed.completedMinutes}
          max={Math.max(m.activity.avgCompletedVsPrescribed.prescribedMinutes, 1)} color="#F59E0B" />
      </SectionCard>

      {/* Weekly Adherence Table */}
      {m.weeklyAdherence.length > 0 && (
        <SectionCard title="Weekly Adherence Log" icon={BarChart3}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span className="admin-pagination-info">
              Showing {adhPage * adhPageSize + 1}–{Math.min((adhPage + 1) * adhPageSize, m.weeklyAdherence.length)} of {m.weeklyAdherence.length}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <select className="admin-page-size-select" value={adhPageSize}
                onChange={e => { setAdhPageSize(Number(e.target.value)); setAdhPage(0); }}>
                {PAGE_SIZES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <div className="admin-pagination-btns">
                <button className="admin-page-btn" disabled={adhPage <= 0} onClick={() => setAdhPage(p => p - 1)}><ChevronLeft size={16} /></button>
                <button className="admin-page-btn" disabled={(adhPage + 1) * adhPageSize >= m.weeklyAdherence.length} onClick={() => setAdhPage(p => p + 1)}><ChevronRight size={16} /></button>
              </div>
            </div>
          </div>
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr><th>Week Start</th><th>User</th><th>Adherent</th><th>Login Streak</th><th>Adherence Streak</th></tr>
              </thead>
              <tbody>
                {m.weeklyAdherence.slice(adhPage * adhPageSize, (adhPage + 1) * adhPageSize).map((w, i) => (
                  <tr key={`${w.userId}-${w.weekStart}-${i}`}>
                    <td>{w.weekStart}</td>
                    <td className="admin-cell-mono">{w.displayUserId || w.name || w.userId.slice(0, 8)}</td>
                    <td style={{ color: w.exerciseAdherent ? '#4A9D6E' : '#EF4444' }}>{w.exerciseAdherent ? 'Yes' : 'No'}</td>
                    <td>{w.loginStreakWeeks}w</td>
                    <td>{w.adherenceStreakWeeks}w</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}
    </div>
  );

  const renderSugar = () => (
    <div className="admin-tab-content">
      <h2 className="admin-tab-title"><Heart size={22} /> Health Data (Sugar Readings)</h2>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={Heart} value={fmt(m.sugarReadings.totalEntries)} label="Total Entries" />
        <MetricCard icon={Heart} value={fmt(m.sugarReadings.fastingCount)} label="Fasting" />
        <MetricCard icon={Heart} value={fmt(m.sugarReadings.postMealCount)} label="Post-Meal" />
        <MetricCard icon={Heart} value={fmt(m.sugarReadings.hba1cCount)} label="HbA1c" />
      </div>
      <MetricCard icon={Activity} value={fmt(m.sugarReadings.usersWithRecentHba1c)} label="Users w/ Recent HbA1c (90d)" />

      {/* Sugar Value-Range Distributions */}
      <div className="admin-scard-row" style={{ marginTop: 16 }}>
        {(m as any).sugarDistributions && (
          <>
            <SectionCard title="Fasting Readings Distribution" icon={BarChart3}>
              <Bar label="Below 100 (normal)" value={(m as any).sugarDistributions.fasting.below100}
                max={Math.max((m as any).sugarDistributions.fasting.below100, (m as any).sugarDistributions.fasting.range100_125, (m as any).sugarDistributions.fasting.above126, 1)}
                color="#4A9D6E" />
              <Bar label="100–125 (pre-diabetic)" value={(m as any).sugarDistributions.fasting.range100_125}
                max={Math.max((m as any).sugarDistributions.fasting.below100, (m as any).sugarDistributions.fasting.range100_125, (m as any).sugarDistributions.fasting.above126, 1)}
                color="#F59E0B" />
              <Bar label="126+ (diabetic)" value={(m as any).sugarDistributions.fasting.above126}
                max={Math.max((m as any).sugarDistributions.fasting.below100, (m as any).sugarDistributions.fasting.range100_125, (m as any).sugarDistributions.fasting.above126, 1)}
                color="#EF4444" />
            </SectionCard>
            <SectionCard title="Post-Meal Readings Distribution" icon={BarChart3}>
              <Bar label="Below 140 (normal)" value={(m as any).sugarDistributions.postMeal.below140}
                max={Math.max((m as any).sugarDistributions.postMeal.below140, (m as any).sugarDistributions.postMeal.range140_199, (m as any).sugarDistributions.postMeal.above200, 1)}
                color="#4A9D6E" />
              <Bar label="140–199 (pre-diabetic)" value={(m as any).sugarDistributions.postMeal.range140_199}
                max={Math.max((m as any).sugarDistributions.postMeal.below140, (m as any).sugarDistributions.postMeal.range140_199, (m as any).sugarDistributions.postMeal.above200, 1)}
                color="#F59E0B" />
              <Bar label="200+ (diabetic)" value={(m as any).sugarDistributions.postMeal.above200}
                max={Math.max((m as any).sugarDistributions.postMeal.below140, (m as any).sugarDistributions.postMeal.range140_199, (m as any).sugarDistributions.postMeal.above200, 1)}
                color="#EF4444" />
            </SectionCard>
          </>
        )}
      </div>
    </div>
  );

  const renderNotifications = () => (
    <div className="admin-tab-content">
      <h2 className="admin-tab-title"><Bell size={22} /> Notifications</h2>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={Bell} value={fmt(m.notifications.pushSent)} label="Sent" />
        <MetricCard icon={Bell} value={fmt(m.notifications.pushDelivered)} label="Delivered" />
        <MetricCard icon={Bell} value={fmt(m.notifications.pushOpened)} label="Opened" />
        <MetricCard icon={Bell} value={fmt(m.notifications.pushActionCompleted)} label="Action Completed" />
      </div>
      <div className="admin-mcard-grid-3">
        <MetricCard icon={Users} value={`${m.notifications.reminderOptInRate}%`} label="Reminder Opt-in Rate"
          sub={`${m.notifications.totalUsersWithReminders} users`} />
      </div>

      <SectionCard title="Broadcast Notification (to all subscribed users)" icon={Send}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
          <button className="admin-action-btn" onClick={() => handleBroadcast('follow_up')} disabled={!!broadcasting}>
            {broadcasting === 'follow_up' ? 'Sending...' : 'Send Follow-up'}
          </button>
          <button className="admin-action-btn" onClick={() => handleBroadcast('exercise_reminder')} disabled={!!broadcasting}>
            {broadcasting === 'exercise_reminder' ? 'Sending...' : 'Send Exercise Reminder'}
          </button>
          <button className="admin-action-btn" onClick={() => handleBroadcast('sugar_test')} disabled={!!broadcasting}>
            {broadcasting === 'sugar_test' ? 'Sending...' : 'Send Sugar Test Reminder'}
          </button>
        </div>
        {broadcastResult && (
          <p className={`admin-msg ${broadcastResult.startsWith('❌') ? 'admin-msg-error' : 'admin-msg-success'}`}>
            {broadcastResult}
          </p>
        )}
        <p style={{ fontSize: 12, color: 'var(--admin-text-sec)', marginTop: 4 }}>
          Sends to all users who have enabled push notifications, regardless of due-date checks.
        </p>
      </SectionCard>
    </div>
  );

  const renderSafety = () => (
    <div className="admin-tab-content">
      <h2 className="admin-tab-title"><Shield size={22} /> Safety</h2>

      <div className="admin-mcard-grid-4">
        <MetricCard icon={AlertTriangle} value={fmt(m.safety.activitySafetyFlags)} label="Activity Safety Flags" color="#EF4444" />
        <MetricCard icon={AlertTriangle} value={fmt(m.safety.followUpSafetyFlags)} label="Follow-up Safety Flags" color="#F59E0B" />
        <MetricCard icon={Shield} value={fmt(m.safety.escalationAdviceCount)} label="Escalation Advice Given" />
      </div>

      <div className="admin-scard-row">
        <SectionCard title="Safety Flag Summary" icon={Shield}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '8px 0' }}>
            <div><span className="admin-stat-label">Total Safety Events</span><span className="admin-stat-value">{m.safety.activitySafetyFlags + m.safety.followUpSafetyFlags}</span></div>
            <div><span className="admin-stat-label">Escalations Given</span><span className="admin-stat-value">{m.safety.escalationAdviceCount}</span></div>
            <div style={{ marginTop: 8 }}>
              <p style={{ fontSize: 12, color: 'var(--admin-text-sec)', marginBottom: 4 }}>Activity flags count exercise sessions where the user reported physical concern. Follow-up flags indicate check-ins where symptoms were reported.</p>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Safety per 1K Sessions" icon={BarChart3}>
          {(() => {
            const totalAct = m.activity.strengthAdherence.totalLogs || 1;
            const totalFu = m.followUps.totalSessions || 1;
            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '8px 0' }}>
                <div><span className="admin-stat-label">Activity flags / 1K sessions</span><span className="admin-stat-value">{((m.safety.activitySafetyFlags / totalAct) * 1000).toFixed(1)}</span></div>
                <div><span className="admin-stat-label">FU flags / 1K sessions</span><span className="admin-stat-value">{((m.safety.followUpSafetyFlags / totalFu) * 1000).toFixed(1)}</span></div>
                <div><span className="admin-stat-label">Escalations / 1K sessions</span><span className="admin-stat-value">{((m.safety.escalationAdviceCount / totalFu) * 1000).toFixed(1)}</span></div>
              </div>
            );
          })()}
        </SectionCard>
      </div>
    </div>
  );

  const renderAudio = () => (
    <div className="admin-tab-content">
      <h2 className="admin-tab-title"><Headphones size={22} /> Audio Assets</h2>

      <SectionCard title="Missing Audio Assets" icon={Headphones}>
        <p style={{ marginBottom: 16 }}>Missing: <strong>{audioMissing}</strong> asset(s)</p>
        <button className="admin-action-btn" onClick={handleGenerateAudio} disabled={audioGenerating}>
          <Play size={16} /> {audioGenerating ? 'Generating...' : 'Generate All'}
        </button>
        {audioMsg && (
          <p className={`admin-msg ${audioGenerating ? 'admin-msg-info' : audioMsg.startsWith('Error') ? 'admin-msg-error' : 'admin-msg-success'}`}
            style={{ marginTop: 12 }}>
            {audioMsg}
          </p>
        )}
      </SectionCard>

      {audioMissingList.length > 0 && (
        <SectionCard title="Missing Asset Details" icon={Headphones}>
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr><th>Questionnaire</th><th>Question</th><th>Language</th><th>Version</th></tr>
              </thead>
              <tbody>
                {audioMissingList.slice(0, 50).map((a, i) => (
                  <tr key={i}>
                    <td className="admin-cell-mono">{a.questionnaireId}</td>
                    <td className="admin-cell-mono">{a.questionId}</td>
                    <td>{a.language === 'ta' ? 'Tamil' : 'English'}</td>
                    <td>{a.questionnaireVersion}</td>
                  </tr>
                ))}
                {audioMissingList.length > 50 && (
                  <tr><td colSpan={4} className="admin-empty">...and {audioMissingList.length - 50} more</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}
    </div>
  );

  const renderBackend = () => (
    <div className="admin-tab-content">
      <h2 className="admin-tab-title"><Database size={22} /> Backend</h2>

      <div className="admin-scard-row">
        <SectionCard title="Server Health" icon={Info}>
          {healthInfo ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '8px 0' }}>
              <div><span className="admin-stat-label">Status</span><span className="admin-stat-value" style={{ color: healthInfo.status === 'ok' ? '#4A9D6E' : '#EF4444' }}>{healthInfo.status}</span></div>
              <div><span className="admin-stat-label">Database</span><span className="admin-stat-value" style={{ color: healthInfo.db === 'connected' ? '#4A9D6E' : '#EF4444' }}>{healthInfo.db}</span></div>
              <div><span className="admin-stat-label">Response Time</span><span className="admin-stat-value">{healthInfo.responseTimeMs}ms</span></div>
              <div><span className="admin-stat-label">Cache Entries</span><span className="admin-stat-value">{healthInfo.cacheEntries}</span></div>
              <div><span className="admin-stat-label">Checked At</span><span className="admin-stat-value">{new Date(healthInfo.timestamp).toLocaleString()}</span></div>
            </div>
          ) : (
            <p style={{ padding: 16 }}>{healthLoading ? 'Loading...' : 'Health check failed to load'}</p>
          )}
        </SectionCard>

        <SectionCard title="Database Backup" icon={Database}>
          <button className="admin-action-btn" onClick={async () => {
            try {
              await adminApi.triggerBackup();
              alert('Backup started in background');
            } catch { alert('Backup trigger failed'); }
          }}>
            <Database size={16} /> Trigger DB Backup
          </button>
          <p style={{ fontSize: 12, color: 'var(--admin-text-sec)', marginTop: 8 }}>
            Also runs automatically every 6 hours on database writes.
          </p>
        </SectionCard>
      </div>

      <div className="admin-scard-row">
        <SectionCard title="Temporary Audio Cache" icon={Headphones}>
          <button className="admin-action-btn" onClick={async () => {
            if (cleanupRunning) return;
            setCleanupRunning(true);
            setCleanupResult('');
            try {
              const r = await adminApi.cleanupTemporaryAudio();
              setCleanupResult(`✅ Deleted ${r.deleted} expired asset(s)`);
            } catch (e: any) {
              setCleanupResult(`❌ ${e.message}`);
            }
            setCleanupRunning(false);
          }} disabled={cleanupRunning}>
            <RefreshCcw size={16} /> {cleanupRunning ? 'Cleaning...' : 'Cleanup Expired Audio Cache'}
          </button>
          {cleanupResult && (
            <p className={`admin-msg ${cleanupResult.startsWith('❌') ? 'admin-msg-error' : 'admin-msg-success'}`}
              style={{ marginTop: 12 }}>
              {cleanupResult}
            </p>
          )}
          <p style={{ fontSize: 12, color: 'var(--admin-text-sec)', marginTop: 8 }}>
            Removes prescription TTS audio cache entries older than 48 hours.
          </p>
        </SectionCard>
      </div>
    </div>
  );

  const TAB_RENDERERS: Record<TabId, () => ReactNode> = {
    overview: renderOverview,
    users: renderUsers,
    assessments: renderAssessments,
    followups: renderFollowUps,
    prescriptions: renderPrescriptions,
    activity: renderActivity,
    sugar: renderSugar,
    notifications: renderNotifications,
    safety: renderSafety,
    audio: renderAudio,
    backend: renderBackend,
  };

  return (
    <div className="admin-layout">
      {/* Sidebar */}
      <aside className={`admin-sidebar ${sidebarOpen ? '' : 'admin-sidebar-collapsed'}`}>
        <div className="admin-sidebar-header">
          <span className="admin-sidebar-logo">{sidebarOpen ? 'DiaFit Admin' : 'DF'}</span>
          <button className="admin-sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <ChevronRight size={16} style={{ transform: sidebarOpen ? 'rotate(180deg)' : '' }} />
          </button>
        </div>
        <nav className="admin-sidebar-nav">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`admin-sidebar-item ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              title={sidebarOpen ? undefined : tab.label}
            >
              <tab.icon size={18} />
              {sidebarOpen && <span>{tab.label}</span>}
            </button>
          ))}
        </nav>
        <div className="admin-sidebar-footer">
          <button className="admin-sidebar-item" onClick={loadAll} title="Refresh data">
            <RefreshCcw size={18} />
            {sidebarOpen && <span>Refresh</span>}
          </button>
          <button className="admin-sidebar-item" onClick={handleLogout} title="Sign out">
            <LogOut size={18} />
            {sidebarOpen && <span>Sign Out</span>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="admin-main">
        <header className="admin-main-header">
          <h1>{TABS.find(t => t.id === activeTab)?.label || 'Dashboard'}</h1>
          <span className="admin-main-timestamp">Updated: {new Date().toLocaleString()}</span>
        </header>
        <div className="admin-main-body">
          {TAB_RENDERERS[activeTab]()}
        </div>
      </main>
    </div>
  );
}
