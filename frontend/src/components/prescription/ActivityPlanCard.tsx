import type { ExerciseSuggestion } from '../../domain/types';

interface Props {
  title: string;
  exercises: ExerciseSuggestion[];
}

export default function ActivityPlanCard({ title, exercises }: Props) {
  if (!exercises || exercises.length === 0) return null;

  return (
    <div className="prescription-card">
      <h3 className="prescription-card-title">{title}</h3>
      <div className="exercise-list">
        {exercises.map((ex, i) => (
          <div key={i} className="exercise-item">
            <div className="exercise-name">{ex.activityName}</div>
            <div className="exercise-meta">
              {ex.intensity && <span className="meta-tag intensity">{ex.intensity}</span>}
              {ex.duration && <span className="meta-tag">{ex.duration}</span>}
              {ex.frequency && <span className="meta-tag">{ex.frequency}</span>}
            </div>
            {ex.safetyReason && <p className="exercise-safety">{ex.safetyReason}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
