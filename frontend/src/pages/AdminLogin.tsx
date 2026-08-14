import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminApi, setToken } from '../services/api/adminClient';
import { Shield, Eye, EyeOff } from 'lucide-react';

export default function AdminLogin() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) { setError('Enter username and password'); return; }
    setLoading(true);
    setError('');
    try {
      const res = await adminApi.login(username, password);
      setToken(res.token);
      navigate('/admin/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    }
    setLoading(false);
  };

  return (
    <div className="admin-login-page">
      <div className="admin-login-card">
        <div className="admin-login-header">
          <Shield size={32} />
          <h1>DiaCare Admin</h1>
          <p>Sign in to access the dashboard</p>
        </div>
        <form className="admin-login-form" onSubmit={handleSubmit}>
          <div className="admin-login-field">
            <label>Username</label>
            <input type="text" value={username} onChange={e => setUsername(e.target.value)}
              placeholder="Enter admin username" autoFocus />
          </div>
          <div className="admin-login-field">
            <label>Password</label>
            <div className="admin-pwd-wrapper">
              <input type={showPwd ? 'text' : 'password'} value={password}
                onChange={e => setPassword(e.target.value)} placeholder="Enter password" />
              <button type="button" className="admin-pwd-toggle" onClick={() => setShowPwd(p => !p)}>
                {showPwd ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>
          {error && <p className="admin-login-error">{error}</p>}
          <button type="submit" className="admin-login-btn" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
