interface PipelineStepProps {
  steps: { id: string; label: string; status: string }[];
  currentStep: string;
  onStepClick?: (stepId: string) => void;
}

const STEP_ICONS: Record<string, string> = {
  background: '🖼️',
  keyframe: '🎨',
  animation: '🎬',
  audio: '🎵',
  lipsync: '👄',
  export: '📦',
};

export default function GenerationPanel({ steps, currentStep, onStepClick }: PipelineStepProps) {
  const currentIdx = steps.findIndex((s) => s.id === currentStep);

  return (
    <div className="glass rounded-xl p-4 border border-accent-500/10">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-sm shadow-lg shadow-amber-500/20">
          ⚡
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">Generation Pipeline</h3>
          <p className="text-[11px] text-gray-500">Per-shot asset generation flow</p>
        </div>
      </div>

      <div className="relative">
        {/* Vertical pipeline */}
        <div className="absolute left-[15px] top-2 bottom-2 w-px bg-accent-500/10" />

        <div className="space-y-1 relative">
          {steps.map((step, idx) => {
            const isActive = step.id === currentStep;
            const isCompleted = step.status === 'completed';
            const isDisabled = idx > currentIdx + 1;

            return (
              <button
                key={step.id}
                onClick={() => !isDisabled && onStepClick?.(step.id)}
                disabled={isDisabled}
                className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-lg transition-all duration-200 text-left ${
                  isActive
                    ? 'bg-accent-500/10 text-white border border-accent-500/20'
                    : isCompleted
                    ? 'text-gray-300 hover:bg-white/[0.04]'
                    : isDisabled
                    ? 'text-gray-600 cursor-not-allowed'
                    : 'text-gray-400 hover:bg-white/[0.04] cursor-pointer'
                }`}
              >
                {/* Step indicator */}
                <span
                  className={`relative z-10 flex items-center justify-center w-[30px] h-[30px] rounded-full text-xs transition-all duration-300 ${
                    isActive
                      ? 'bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-lg shadow-amber-500/20 scale-110'
                      : isCompleted
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-surface-700 text-gray-500'
                  }`}
                >
                  {isCompleted ? (
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  ) : (
                    <span>{STEP_ICONS[step.id] || '○'}</span>
                  )}
                </span>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${isActive ? 'text-white' : ''}`}>
                      {step.label}
                    </span>
                    {isActive && (
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                    )}
                  </div>
                  <p className={`text-[10px] ${isActive ? 'text-amber-400/70' : 'text-gray-600'}`}>
                    {step.status.replace(/_/g, ' ')}
                  </p>
                </div>

                {/* Arrow for next step */}
                {idx < steps.length - 1 && (
                  <svg
                    className={`w-3.5 h-3.5 shrink-0 transition-colors ${
                      isActive ? 'text-accent-500/30' : 'text-gray-700'
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={1.5}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
