import type { PersonalizedTip } from '../../domain/types';
import { Lightbulb, ShieldAlert } from 'lucide-react';

interface Props {
  title: string;
  tips: PersonalizedTip[];
  safetyWarnings?: string[];
}

export default function TipsCard({ title, tips, safetyWarnings }: Props) {
  return (
    <div className="prescription-card tips-card">
      <h3 className="prescription-card-title">{title}</h3>

      {safetyWarnings && safetyWarnings.length > 0 && (
        <div className="safety-warnings">
          <h4 className="safety-title"><ShieldAlert size={16} /> Safety</h4>
          {safetyWarnings.map((w, i) => (
            <p key={i} className="safety-item">{w}</p>
          ))}
        </div>
      )}

      {tips && tips.length > 0 && (
        <div className="tips-list">
          {tips.map((tip, i) => (
            <div key={i} className="tip-item">
              <Lightbulb size={16} className="tip-icon" />
              <div>
                <p className="tip-text">{tip.tipText}</p>
                {tip.rationale && <p className="tip-rationale">{tip.rationale}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
