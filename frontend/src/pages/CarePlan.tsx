import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useUserStore } from '../stores/useUserStore';
import { translations } from '../data/translations';
import api from '../services/api/client';
import CarePlanView from '../components/careplan/CarePlanView';
import LoadingSpinner from '../components/common/LoadingSpinner';
import AppBar from '../components/common/AppBar';
import BottomNav from '../components/common/BottomNav';
import type { CarePlanSnapshot } from '../domain/types';
import { FileText } from 'lucide-react';

export default function CarePlan() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const t = translations[language];
  const [plan, setPlan] = useState<CarePlanSnapshot | null>(null);
  const [carePlanId, setCarePlanId] = useState<string | null>(null);
  const [riskTier, setRiskTier] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) { navigate('/'); return; }
    const fetchCarePlan = async () => {
      try {
        setLoading(true);
        let data: any;
        if (id && id !== 'latest') {
          data = await api.getCarePlan(id);
        } else {
          data = await api.getLatestCarePlan(user.id);
        }
        if (data?.plan_snapshot) {
          setPlan(data.plan_snapshot);
          setCarePlanId(data.id || null);
          setRiskTier(data.risk_tier || null);
        } else {
          setError('No care plan found. Complete the conversation first.');
        }
      } catch (e: any) {
        setError(e.message || 'Failed to load care plan');
      } finally {
        setLoading(false);
      }
    };
    fetchCarePlan();
  }, [user, id]);

  return (
    <div className="page-container">
      <AppBar
        title={t.viewPlan}
        showBack
        onBack={() => navigate('/home')}
      />

      <main className="page-content">
        {loading && <LoadingSpinner text="Loading your plan..." />}

        {error && (
          <motion.div
            className="error-state"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <FileText size={48} className="error-icon" />
            <p>{error}</p>
            <button className="btn-primary" onClick={() => navigate('/conversation/1')}>
              {t.startAssessment}
            </button>
          </motion.div>
        )}

        {plan && <CarePlanView plan={plan} riskTier={riskTier} carePlanId={carePlanId} />}
      </main>

      <BottomNav />
    </div>
  );
}
