interface Props {
  hasBackground: boolean;
  hasKeyframe: boolean;
  hasAudio: boolean;
  hasLipsync?: boolean;
  onGenerateBackground: () => void;
  onGenerateKeyframe: () => void;
  onGenerateAudio: () => void;
  onGenerateLipSync?: () => void;
  loading?: string | null;
}

export default function GenerationPanel({
  hasBackground,
  hasKeyframe,
  hasAudio,
  hasLipsync,
  onGenerateBackground,
  onGenerateKeyframe,
  onGenerateAudio,
  onGenerateLipSync,
  loading,
}: Props) {
  const btn = (label: string, done: boolean, onClick: () => void, key: string) => (
    <button
      onClick={onClick}
      disabled={done || loading === key}
      className={`px-3 py-1.5 text-xs rounded font-medium transition-colors ${
        done
          ? 'bg-green-700 text-green-200 cursor-default'
          : loading === key
          ? 'bg-gray-700 text-gray-400 animate-pulse'
          : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
      }`}
    >
      {done ? '✓ ' : loading === key ? '... ' : ''}
      {label}
    </button>
  );

  return (
    <div className="flex gap-2 items-center flex-wrap">
      {btn('Background', hasBackground, onGenerateBackground, 'bg')}
      {btn('Keyframe', hasKeyframe, onGenerateKeyframe, 'kf')}
      {btn('Audio', hasAudio, onGenerateAudio, 'audio')}
      {onGenerateLipSync && btn('Lip Sync', !!hasLipsync, onGenerateLipSync, 'ls')}
    </div>
  );
}
