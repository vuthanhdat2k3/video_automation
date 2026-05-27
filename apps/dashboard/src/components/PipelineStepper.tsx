import { useLocation, useParams, Link } from 'react-router-dom';
import { PIPELINE_STEPS } from '../types';

const STEP_COLORS: Record<string, string> = {
  story: 'from-blue-500 to-blue-600',
  characters: 'from-emerald-500 to-emerald-600',
  timeline: 'from-violet-500 to-violet-600',
  shots: 'from-amber-500 to-amber-600',
  export: 'from-pink-500 to-pink-600',
};

export default function PipelineStepper() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();

  if (!id) return null;

  const currentPath = location.pathname.split('/').pop() || '';

  const getStepStatus = (stepId: string) => {
    const idx = PIPELINE_STEPS.findIndex((s) => s.id === stepId);
    const currentIdx = PIPELINE_STEPS.findIndex(
      (s) => currentPath === s.id || (stepId === 'shots' && currentPath === 'scenes')
    );
    if (currentIdx < 0) return 'pending';
    if (idx < currentIdx) return 'completed';
    if (idx === currentIdx) return 'active';
    return 'pending';
  };

  return (
    <div className="hidden md:flex items-center gap-0 bg-surface-800/80 rounded-xl px-1 py-1 border border-accent-500/10">
      {PIPELINE_STEPS.map((step, idx) => {
        const status = getStepStatus(step.id);
        const isActive = status === 'active';
        const isCompleted = status === 'completed';

        return (
          <Link
            key={step.id}
            to={`/projects/${id}/${step.id}`}
            className={`group flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 relative ${
              isActive
                ? 'bg-accent-500/10 text-white shadow-sm'
                : isCompleted
                ? 'text-gray-300 hover:text-white hover:bg-white/5'
                : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
            }`}
          >
            {/* Step number circle */}
            <span
              className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-br ' + STEP_COLORS[step.id] + ' text-white shadow-lg shadow-accent-500/20'
                  : isCompleted
                  ? 'bg-accent-500/20 text-accent-400'
                  : 'bg-surface-600 text-gray-500'
              }`}
            >
              {isCompleted ? (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              ) : (
                idx + 1
              )}
            </span>

            <span className={`text-sm font-medium hidden lg:block ${isActive ? '' : ''}`}>
              {step.label}
            </span>

            {/* Arrow between steps */}
            {idx < PIPELINE_STEPS.length - 1 && (
              <svg
                className={`w-4 h-4 ml-1 hidden lg:block transition-colors ${
                  isCompleted ? 'text-accent-500/40' : 'text-gray-600'
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            )}
          </Link>
        );
      })}
    </div>
  );
}
