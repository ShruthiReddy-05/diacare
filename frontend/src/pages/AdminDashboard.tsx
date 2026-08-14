import { useEffect, useState, useRef, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminApi, clearToken, isAdminLoggedIn, exportToCsv, type OverviewMetrics, type HealthInfo, type AdminUserRow } from '../services/api/adminClient';
import {
  LayoutDashboard, Users, RefreshCcw, AlertTriangle,
  Heart, Bell, Shield, LogOut, Search, Headphones, Play,
  Send, Database, Download, X, BarChart3,
  type LucideIcon,
} from 'lucide-react';

type TabId = 'overview' | 'users' | 'export' | 'notifications' | 'audio' | 'backend';

const TABS: { id: TabId; label: string; icon: LucideIcon }[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'users', label: 'Users', icon: Users },
  { id: 'export', label: 'Export', icon: Download },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'audio', label: 'Audio Assets', icon: Headphones },
  { id: 'backend', label: 'Backend', icon: Database },
];

const RISK_COLORS: Record<string, string> = { red: '#EF4444', amber: '#F59E0B', green: '#10B981' };

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // ── Users tab ──
  const [usersList, setUsersList] = useState<AdminUserRow[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersPage, setUsersPage] = useState(1);
  const usersLimit = 10;
  const [usersTotalPages, setUsersTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [detailUser, setDetailUser] = useState<AdminUserRow | null>(null);
  const [detailData, setDetailData] = useState<any>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // ── Audio tab ──
  const [audioMissing, setAudioMissing] = useState(0);
  const [audioGenerating, setAudioGenerating] = useState(false);
  const [audioMsg, setAudioMsg] = useState('');

  // ── Notifications tab ──
  const [broadcasting, setBroadcasting] = useState<string | null>(null);
  const [broadcastResult, setBroadcastResult] = useState('');

  // ── Export tab ──
  const [exporting, setExporting] = useState<'responses' | 'checkins' | null>(null);
  const [exportMsg, setExportMsg] = useState('');

  // ── Backend tab ──
  const [healthInfo, setHealthInfo] = useState<HealthInfo | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [cleanupRunning, setCleanupRunning] = useState(false);
  const [cleanupResult, setCleanupResult] = useState('');
  const [backupResult, setBackupResult] = useState('');

  useEffect(() => {
    if (!isAdminLoggedIn()) { navigate('/admin'); return; }
    loadOverview();
  }, []);

  useEffect(() => {
    if (activeTab === 'users') loadUsers();
    if (activeTab === 'audio') checkMissingAudio();
    if (activeTab === 'backend') loadHealth();
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'users') loadUsers();
  }, [usersPage]);

  const loadOverview = async () => {
    setLoading(true);
    try {
      const m = await adminApi.getOverviewMetrics();
      setMetrics(m);
    } catch (e: any) {
      if (e.message === 'Unauthorized') navigate('/admin');
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const res = await adminApi.getUsers({ search, page: usersPage, limit: usersLimit });
      setUsersList(res.users);
      setUsersTotal(res.total);
      setUsersTotalPages(res.totalPages);
    } catch { /* ignore */ }
  };

  const handleSearchChange = (e: ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      setUsersPage(1);
      loadUsers();
    }, 350);
  };

  const checkMissingAudio = async () => {
    try {
      const res = await adminApi.getMissingAudio();
      setAudioMissing(res.total);
    } catch { /* ignore */ }
  };

  const handleGenerateAudio = async () => {
    setAudioGenerating(true);
    setAudioMsg('');
    try {
      const res = await adminApi.generateAudio({});
      setAudioMsg(`Generated ${res.generated}, skipped ${res.skipped}, failed ${res.failed}.`);
      checkMissingAudio();
    } catch (e: any) {
      setAudioMsg(e.message || 'Failed to generate audio');
    } finally {
      setAudioGenerating(false);
    }
  };

  const handleBroadcast = async (type: 'checkin' | 'medication_reminder' | 'sugar_test') => {
    setBroadcasting(type);
    setBroadcastResult('');
    try {
      const res = await adminApi.broadcastNotification(type);
      setBroadcastResult(`Sent to ${res.sent}/${res.totalUsersWithSubscriptions} subscribed users (${res.failed} failed).`);
    } catch (e: any) {
      setBroadcastResult(e.message || 'Broadcast failed');
    } finally {
      setBroadcasting(null);
    }
  };

  const handleUserClick = async (user: AdminUserRow) => {
    setDetailUser(user);
    setDetailLoading(true);
    try {
      const data = await adminApi.getUserDetail(user.id);
      setDetailData(data);
    } catch { /* ignore */ } finally {
      setDetailLoading(false);
    }
  };

  const loadHealth = async () => {
    setHealthLoading(true);
    try {
      const h = await adminApi.getHealth();
      setHealthInfo(h);
    } catch { /* ignore */ } finally {
      setHealthLoading(false);
    }
  };

  const handleLogout = () => {
    clearToken();
    navigate('/admin');
  };

  const exportUsers = () => exportToCsv(usersList, 'diafit_users.csv');

  const handleExportResponses = async () => {
    setExporting('responses');
    setExportMsg('');
    try {
      const rows = await adminApi.exportResponses();
      if (!rows.length) { setExportMsg('No assessment responses recorded yet.'); return; }
      exportToCsv(rows, `diafit_assessment_responses_${new Date().toISOString().slice(0, 10)}.csv`);
    } catch (e: any) {
      setExportMsg(e.message || 'Export failed');
    } finally {
      setExporting(null);
    }
  };

  const handleExportCheckins = async () => {
    setExporting('checkins');
    setExportMsg('');
    try {
      const rows = await adminApi.exportCheckins();
      if (!rows.length) { setExportMsg('No weekly check-ins recorded yet.'); return; }
      exportToCsv(rows, `diafit_weekly_checkins_${new Date().toISOString().slice(0, 10)}.csv`);
    } catch (e: any) {
      setExportMsg(e.message || 'Export failed');
    } finally {
      setExporting(null);
    }
  };

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="admin-spinner" />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="admin-layout">
      <aside className={`admin-sidebar ${sidebarOpen ? '' : 'admin-sidebar-collapsed'}`}>
        <div className="admin-sidebar-header">
          {sidebarOpen && <span className="admin-sidebar-logo">DiaFit Admin</span>}
          <button onClick={() => setSidebarOpen(o => !o)} className="admin-sidebar-toggle">
            <LayoutDashboard size={18} />
          </button>
        </div>
        <nav className="admin-sidebar-nav">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`admin-sidebar-item ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <tab.icon size={18} />
              {sidebarOpen && <span>{tab.label}</span>}
            </button>
          ))}
        </nav>
        <div className="admin-sidebar-footer">
          <button className="admin-sidebar-item" onClick={handleLogout}>
            <LogOut size={18} />
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </aside>

      <main className="admin-main">
        <div className="admin-main-body">
          {activeTab === 'overview' && metrics && (
            <div className="admin-tab-content">
              <h1 className="admin-tab-title"><LayoutDashboard size={20} /> Overview</h1>
              <div className="admin-mcard-grid-3">
                <div className="admin-mcard"><Users size={22} /><div><span className="admin-mcard-value">{metrics.totalUsers}</span><span className="admin-mcard-label">Total Users</span></div></div>
                <div className="admin-mcard"><Users size={22} /><div><span className="admin-mcard-value">{metrics.activeToday}</span><span className="admin-mcard-label">Active Today</span></div></div>
                <div className="admin-mcard"><Users size={22} /><div><span className="admin-mcard-value">{metrics.activeThisWeek}</span><span className="admin-mcard-label">Active This Week</span></div></div>
                <div className="admin-mcard"><BarChart3 size={22} /><div><span className="admin-mcard-value">{metrics.baselineCompleted}</span><span className="admin-mcard-label">Baseline Completed</span></div></div>
                <div className="admin-mcard"><RefreshCcw size={22} /><div><span className="admin-mcard-value">{metrics.conversationSessionsInProgress}</span><span className="admin-mcard-label">Sessions In Progress</span></div></div>
                <div className="admin-mcard"><Shield size={22} /><div><span className="admin-mcard-value">{metrics.openSafetyEvents}</span><span className="admin-mcard-label">Open Safety Events</span></div></div>
              </div>

              <div className="admin-scard">
                <h3 className="admin-scard-title"><AlertTriangle size={18} /> Risk Tier Distribution</h3>
                {metrics.riskTierDistribution.map(r => {
                  const pct = metrics.totalUsers > 0 ? Math.round((r.count / metrics.totalUsers) * 100) : 0;
                  return (
                    <div key={r.tier} className="admin-bar-row">
                      <span className="admin-bar-label">{r.tier}</span>
                      <div className="admin-bar-track"><div className="admin-bar-fill" style={{ width: `${pct}%`, background: RISK_COLORS[r.tier] }} /></div>
                      <span className="admin-bar-value">{r.count}</span>
                    </div>
                  );
                })}
              </div>

              <div className="admin-scard">
                <h3 className="admin-scard-title"><RefreshCcw size={18} /> Weekly Check-Ins</h3>
                {(() => {
                  const max = metrics.checkinsCompleted + metrics.checkinsMissed + metrics.checkinsEscalated || 1;
                  return (
                    <>
                      <div className="admin-bar-row"><span className="admin-bar-label">Completed</span><div className="admin-bar-track"><div className="admin-bar-fill" style={{ width: `${Math.round(metrics.checkinsCompleted / max * 100)}%`, background: '#10B981' }} /></div><span className="admin-bar-value">{metrics.checkinsCompleted}</span></div>
                      <div className="admin-bar-row"><span className="admin-bar-label">Missed</span><div className="admin-bar-track"><div className="admin-bar-fill" style={{ width: `${Math.round(metrics.checkinsMissed / max * 100)}%`, background: '#F59E0B' }} /></div><span className="admin-bar-value">{metrics.checkinsMissed}</span></div>
                      <div className="admin-bar-row"><span className="admin-bar-label">Escalated</span><div className="admin-bar-track"><div className="admin-bar-fill" style={{ width: `${Math.round(metrics.checkinsEscalated / max * 100)}%`, background: '#EF4444' }} /></div><span className="admin-bar-value">{metrics.checkinsEscalated}</span></div>
                    </>
                  );
                })()}
                {metrics.reassessmentsTriggered > 0 && (
                  <p className="admin-msg admin-msg-info">{metrics.reassessmentsTriggered} user(s) flagged for full reassessment (two consecutive poor weeks).</p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="admin-tab-content">
              <div className="admin-tab-header-row">
                <h1 className="admin-tab-title"><Users size={20} /> Users</h1>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <div className="admin-search-wrapper">
                    <Search size={16} />
                    <input className="admin-search-input" placeholder="Search by name or ID..." value={search} onChange={handleSearchChange} />
                  </div>
                  <button className="admin-action-btn" onClick={exportUsers}><Download size={16} /> Export CSV</button>
                </div>
              </div>

              <div className="admin-table-wrapper">
                <table className="admin-table">
                  <thead>
                    <tr><th>Display ID</th><th>Name</th><th>Language</th><th>Risk Tier</th><th>Check-ins Due</th></tr>
                  </thead>
                  <tbody>
                    {usersList.map(u => (
                      <tr key={u.id} className="admin-clickable-row" onClick={() => handleUserClick(u)}>
                        <td className="admin-cell-mono">{u.displayUserId}</td>
                        <td>{u.firstName} {u.lastName}</td>
                        <td>{u.preferredLanguage}</td>
                        <td style={{ color: RISK_COLORS[u.riskTier] || 'inherit' }}>{u.riskTier}</td>
                        <td>{u.checkinsDue}</td>
                      </tr>
                    ))}
                    {usersList.length === 0 && (
                      <tr><td colSpan={5} className="admin-empty">No users found.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16 }}>
                <span className="admin-pagination-info">Page {usersPage} of {usersTotalPages || 1} ({usersTotal} users)</span>
                <div className="admin-pagination-btns">
                  <button className="admin-page-btn" disabled={usersPage <= 1} onClick={() => setUsersPage(p => p - 1)}>‹</button>
                  <button className="admin-page-btn" disabled={usersPage >= usersTotalPages} onClick={() => setUsersPage(p => p + 1)}>›</button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'export' && (
            <div className="admin-tab-content">
              <h1 className="admin-tab-title"><Download size={20} /> Export</h1>
              <div className="admin-scard">
                <h3 className="admin-scard-title">All Assessment Responses</h3>
                <p className="admin-audio-status">Every baseline/module answer from every user, one row per question -- downloads as a .csv file that opens directly in Excel.</p>
                <div className="admin-audio-actions">
                  <button className="admin-action-btn" disabled={!!exporting} onClick={handleExportResponses}>
                    <Download size={16} /> {exporting === 'responses' ? 'Exporting...' : 'Export Responses'}
                  </button>
                </div>
              </div>
              <div className="admin-scard">
                <h3 className="admin-scard-title">Weekly Check-Ins</h3>
                <p className="admin-audio-status">Every weekly check-in answer from every user, one row per check-in -- downloads as a .csv file that opens directly in Excel.</p>
                <div className="admin-audio-actions">
                  <button className="admin-action-btn" disabled={!!exporting} onClick={handleExportCheckins}>
                    <Download size={16} /> {exporting === 'checkins' ? 'Exporting...' : 'Export Check-Ins'}
                  </button>
                </div>
              </div>
              {exportMsg && <p className="admin-msg admin-msg-info">{exportMsg}</p>}
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="admin-tab-content">
              <h1 className="admin-tab-title"><Bell size={20} /> Notifications</h1>
              <div className="admin-scard">
                <h3 className="admin-scard-title"><Send size={18} /> Broadcast</h3>
                <p className="admin-audio-status">Send a push notification to every subscribed user.</p>
                <div className="admin-audio-actions">
                  <button className="admin-action-btn" disabled={!!broadcasting} onClick={() => handleBroadcast('checkin')}>
                    {broadcasting === 'checkin' ? 'Sending...' : 'Weekly Check-In'}
                  </button>
                  <button className="admin-action-btn" disabled={!!broadcasting} onClick={() => handleBroadcast('medication_reminder')}>
                    {broadcasting === 'medication_reminder' ? 'Sending...' : 'Medication Reminder'}
                  </button>
                  <button className="admin-action-btn" disabled={!!broadcasting} onClick={() => handleBroadcast('sugar_test')}>
                    {broadcasting === 'sugar_test' ? 'Sending...' : 'Sugar Test Reminder'}
                  </button>
                </div>
                {broadcastResult && <p className="admin-msg admin-msg-info">{broadcastResult}</p>}
              </div>
            </div>
          )}

          {activeTab === 'audio' && (
            <div className="admin-tab-content">
              <h1 className="admin-tab-title"><Headphones size={20} /> Audio Assets</h1>
              <div className="admin-scard">
                <h3 className="admin-scard-title">Pre-recorded Question Prompts</h3>
                <p className="admin-audio-status">{audioMissing} question prompt(s) missing pre-generated audio.</p>
                <div className="admin-audio-actions">
                  <button className="admin-action-btn" disabled={audioGenerating} onClick={handleGenerateAudio}>
                    <Play size={16} /> {audioGenerating ? 'Generating...' : 'Generate Missing Audio'}
                  </button>
                </div>
                {audioMsg && <p className="admin-msg admin-msg-info">{audioMsg}</p>}
              </div>
            </div>
          )}

          {activeTab === 'backend' && (
            <div className="admin-tab-content">
              <h1 className="admin-tab-title"><Database size={20} /> Backend</h1>
              <div className="admin-scard">
                <h3 className="admin-scard-title">Health</h3>
                {healthLoading && <p className="admin-audio-status">Checking...</p>}
                {healthInfo && (
                  <>
                    <p className="admin-audio-status">Status: {healthInfo.status} | DB: {healthInfo.db} | {healthInfo.responseTimeMs}ms</p>
                    <div className="admin-audio-actions"><button className="admin-action-btn" onClick={loadHealth}><RefreshCcw size={16} /> Refresh</button></div>
                  </>
                )}
              </div>

              <div className="admin-scard">
                <h3 className="admin-scard-title">Backup</h3>
                <div className="admin-audio-actions">
                  <button className="admin-action-btn" onClick={async () => {
                    try {
                      const res = await adminApi.triggerBackup();
                      setBackupResult(res.message);
                    } catch (e: any) {
                      setBackupResult(e.message || 'Backup failed');
                    }
                  }}>Trigger Manual Backup</button>
                </div>
                {backupResult && <p className="admin-msg admin-msg-info">{backupResult}</p>}
              </div>

              <div className="admin-scard">
                <h3 className="admin-scard-title"><Heart size={18} /> Temporary Audio Cleanup</h3>
                <div className="admin-audio-actions">
                  <button className="admin-action-btn" disabled={cleanupRunning} onClick={async () => {
                    setCleanupRunning(true);
                    try {
                      const res = await adminApi.cleanupTemporaryAudio();
                      setCleanupResult(res.message);
                    } catch (e: any) {
                      setCleanupResult(e.message || 'Cleanup failed');
                    } finally {
                      setCleanupRunning(false);
                    }
                  }}>{cleanupRunning ? 'Cleaning...' : 'Clean Up Expired Audio'}</button>
                </div>
                {cleanupResult && <p className="admin-msg admin-msg-info">{cleanupResult}</p>}
              </div>
            </div>
          )}
        </div>
      </main>

      {detailUser && (
        <div className="admin-modal-overlay" onClick={() => { setDetailUser(null); setDetailData(null); }}>
          <div className="admin-modal" onClick={e => e.stopPropagation()}>
            <div className="admin-modal-header">
              <h3>{detailUser.firstName} {detailUser.lastName} ({detailUser.displayUserId})</h3>
              <button className="admin-modal-close" onClick={() => { setDetailUser(null); setDetailData(null); }}><X size={20} /></button>
            </div>
            <div className="admin-modal-body">
              {detailLoading && <p className="admin-audio-status">Loading...</p>}
              {detailData && (
                <>
                  {detailData.baselineProfile && (
                    <div>
                      <h3 className="admin-scard-title">Baseline Profile</h3>
                      <div className="admin-detail-row"><span>Risk tier</span><span>{detailData.baselineProfile.overallRiskTier || '--'}</span></div>
                      <div className="admin-detail-row"><span>BMI category</span><span>{detailData.baselineProfile.bmiCategory || '--'}</span></div>
                      <div className="admin-detail-row"><span>Glycemic category</span><span>{detailData.baselineProfile.glycemicCategory || '--'}</span></div>
                    </div>
                  )}
                  <div>
                    <h3 className="admin-scard-title">Check-In Sessions ({detailData.checkinSessions.length})</h3>
                    {detailData.checkinSessions.slice(0, 8).map((c: any) => (
                      <div key={c.id} className="admin-detail-row"><span>Week {c.programWeek}</span><span>{c.status} ({c.dueDate})</span></div>
                    ))}
                  </div>
                  <div>
                    <h3 className="admin-scard-title">Safety Events ({detailData.safetyEvents.length})</h3>
                    {detailData.safetyEvents.slice(0, 8).map((e: any) => (
                      <div key={e.id} className="admin-detail-row"><span>{e.triggerCode}</span><span>{e.resolved ? 'resolved' : 'open'}</span></div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
