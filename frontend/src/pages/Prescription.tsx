import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useUserStore } from '../stores/useUserStore';
import { translations } from '../data/translations';
import api from '../services/api/client';
import PrescriptionView from '../components/prescription/PrescriptionView';
import LoadingSpinner from '../components/common/LoadingSpinner';
import AppBar from '../components/common/AppBar';
import BottomNav from '../components/common/BottomNav';
import type { AiExercisePrescription } from '../domain/types';
import { FileText } from 'lucide-react';

export default function Prescription() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { language, user } = useUserStore();
  const t = translations[language];
  const [prescription, setPrescription] = useState<AiExercisePrescription | null>(null);
  const [prescriptionId, setPrescriptionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) { navigate('/'); return; }
    const fetchPrescription = async () => {
      try {
        setLoading(true);
        let data: any;
        if (id && id !== 'latest') {
          data = await api.getPrescription(id);
        } else {
          data = await api.getLatestPrescription(user.id);
        }
        if (data?.prescription_snapshot) {
          setPrescription(data.prescription_snapshot);
          setPrescriptionId(data.id || null);
        } else {
          setError('No prescription found. Complete an assessment first.');
        }
      } catch (e: any) {
        setError(e.message || 'Failed to load prescription');
      } finally {
        setLoading(false);
      }
    };
    fetchPrescription();
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
            <button className="btn-primary" onClick={() => navigate('/assessment')}>
              {t.startAssessment}
            </button>
          </motion.div>
        )}

        {prescription && <PrescriptionView prescription={prescription} prescriptionId={prescriptionId} />}
      </main>

      <BottomNav />
    </div>
  );
}
