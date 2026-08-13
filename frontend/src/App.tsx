import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useUserStore } from './stores/useUserStore'
import LoadingSpinner from './components/common/LoadingSpinner'
import FirstLandingPage from './components/registration/FirstLandingPage'
import RecoverProfilePage from './components/registration/RecoverProfilePage'
import Home from './pages/Home'
import Assessment from './pages/Assessment'
import Prescription from './pages/Prescription'
import History from './pages/History'
import SugarTracking from './pages/SugarTracking'
import ActivityProgress from './pages/ActivityProgress'
import FollowUp from './pages/FollowUp'
import Settings from './pages/Settings'
import AdminLogin from './pages/AdminLogin'
import AdminDashboard from './pages/AdminDashboard'

function App() {
  const { loadFromLocal, isLoading, isRegistered, language } = useUserStore()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    loadFromLocal().finally(() => setReady(true))
  }, [])

  useEffect(() => {
    document.documentElement.lang = language === 'ta' ? 'ta' : 'en';
  }, [language]);

  if (!ready || isLoading) {
    return (
      <div className="loading-screen">
        <LoadingSpinner text="DiaFit Coach" />
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={isRegistered ? <Navigate to="/home" /> : <FirstLandingPage />} />
        <Route path="/recover" element={<RecoverProfilePage />} />
        <Route path="/home" element={isRegistered ? <Home /> : <Navigate to="/" />} />
        <Route path="/assessment" element={isRegistered ? <Assessment /> : <Navigate to="/" />} />
        <Route path="/prescription/:id" element={isRegistered ? <Prescription /> : <Navigate to="/" />} />
        <Route path="/history" element={isRegistered ? <History /> : <Navigate to="/" />} />
        <Route path="/sugar" element={isRegistered ? <SugarTracking /> : <Navigate to="/" />} />
        <Route path="/activity" element={isRegistered ? <ActivityProgress /> : <Navigate to="/" />} />
        <Route path="/follow-up" element={isRegistered ? <FollowUp /> : <Navigate to="/" />} />
        <Route path="/settings" element={isRegistered ? <Settings /> : <Navigate to="/" />} />
        <Route path="/admin" element={<AdminLogin />} />
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
