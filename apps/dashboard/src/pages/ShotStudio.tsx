import { useParams, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getShots,
  createShot,
  deleteShot,
  generateBackground,
  generateKeyframe,
  generateAudio,
  generateLipSync,
  exportScene,
  updateShot,
  getAssetDownloadUrl,
} from '../api/endpoints';
import { useJobProgress } from '../hooks/useJobProgress';
import GenerationPanel from '../components/GenerationPanel';
import { useState, useEffect } from 'react';

const GENERATION_STEPS = [
  { id: 'background', label: 'Background' },
  { id: 'keyframe', label: 'Keyframe' },
  { id: 'audio', label: 'Audio' },
  { id: 'lipsync', label: 'Lip Sync' },
];

export default function ShotStudio() {
  const { id, sid } = useParams<{ id: string; sid: string }>();
  const [searchParams] = useSearchParams();
  const qc = useQueryClient();
  const [loadingKey, setLoadingKey] = useState<string | null>(null);
  
  const { data: shots, isLoading } = useQuery({
    queryKey: ['shots', sid],
    queryFn: () => getShots(sid!),
    enabled: !!sid,
  });

  const { jobs } = useJobProgress(id);

  useEffect(() => {
    if (jobs?.length) {
      qc.invalidateQueries({ queryKey: ['shots', sid] });
    }
  }, [jobs, sid, qc]);

  const selectedShotId = searchParams.get('shot');
  const selectedShot = shots?.find((s: any) => s.id === selectedShotId);
  const activeShot: any = selectedShot || shots?.[0];

  const [shotDesc, setShotDesc] = useState('');

  useEffect(() => {
    if (activeShot) {
      setShotDesc(activeShot.description || '');
    }
  }, [activeShot]);

  const updateShotMut = useMutation({
    mutationFn: (desc: string) => updateShot(activeShot.id, { description: desc } as any),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shots', sid] });
    },
  });

  const createMut = useMutation({
    mutationFn: () =>
      createShot(sid!, {
        order_index: (shots?.length || 0),
        duration_seconds: 4,
        description: '',
      } as any),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['shots', sid] }),
  });

  const delMut = useMutation({
    mutationFn: (shotId: string) => deleteShot(shotId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['shots', sid] }),
  });

  const doGen = async (shotId: string, fn: (id: string) => Promise<any>, key: string) => {
    setLoadingKey(key);
    try {
      await fn(shotId);
      qc.invalidateQueries({ queryKey: ['shots', sid] });
    } finally {
      setLoadingKey(null);
    }
  };

  const exportMut = useMutation({
    mutationFn: () => exportScene(sid!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['shots', sid] }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-500/30 border-t-accent-500 rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading shots...</p>
        </div>
      </div>
    );
  }

  const allBg = (shots || []).every((s: any) => s.background_asset_id);
  const allKf = (shots || []).every((s: any) => s.keyframe_asset_id);
  const allAudio = (shots || []).every((s: any) => s.audio_asset_id);
  const allReady = allBg && allKf && allAudio;

  const hasDescChanges = activeShot && shotDesc !== (activeShot.description || '');

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Shot Studio</h1>
          <p className="text-sm text-gray-500 mt-1">
            {shots?.length || 0} shot{(shots?.length || 0) !== 1 ? 's' : ''} in this scene
          </p>
        </div>
        <div className="flex gap-2">
          {shots && shots.length > 0 && allReady && (
            <button
              onClick={() => exportMut.mutate()}
              disabled={exportMut.isPending}
              className="btn-primary flex items-center gap-2"
            >
              {exportMut.isPending ? (
                <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Exporting...</>
              ) : (
                <><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                </svg> Export Scene</>
              )}
            </button>
          )}
          <button
            onClick={() => createMut.mutate()}
            disabled={createMut.isPending}
            className="btn-secondary flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Add Shot
          </button>
        </div>
      </div>

      {shots && shots.length > 0 ? (
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          {/* Shot List */}
          <div className="xl:col-span-1 space-y-2">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">All Shots</h3>
            {shots.map((shot: any) => {
              const isSelected = activeShot?.id === shot.id;
              const stepCount = [shot.background_asset_id, shot.keyframe_asset_id, shot.audio_asset_id].filter(Boolean).length;
              return (
                <button
                  key={shot.id}
                  onClick={() => {
                    const params = new URLSearchParams(searchParams);
                    params.set('shot', shot.id);
                    window.history.replaceState(null, '', `?${params.toString()}`);
                    qc.invalidateQueries({ queryKey: ['shots', sid] });
                  }}
                  className={`w-full text-left p-3 rounded-xl transition-all ${
                    isSelected
                      ? 'bg-accent-500/10 border border-accent-500/25'
                      : 'card hover:border-accent-500/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-white">Shot {shot.order_index + 1}</span>
                    <span className="text-[10px] text-gray-500">{shot.duration_seconds}s</span>
                  </div>
                  <p className="text-[10px] text-gray-500 line-clamp-1 mb-1.5">
                    {shot.shot_type} · {shot.camera?.framing || 'medium'}
                  </p>
                  <div className="flex gap-1">
                    <span className={`w-5 h-1.5 rounded-full ${shot.background_asset_id ? 'bg-emerald-500' : 'bg-surface-600'}`} />
                    <span className={`w-5 h-1.5 rounded-full ${shot.keyframe_asset_id ? 'bg-blue-500' : 'bg-surface-600'}`} />
                    <span className={`w-5 h-1.5 rounded-full ${shot.audio_asset_id ? 'bg-violet-500' : 'bg-surface-600'}`} />
                    <span className={`w-5 h-1.5 rounded-full ${shot.video_export_id ? 'bg-amber-500' : 'bg-surface-600'}`} />
                  </div>
                  <div className="text-[9px] text-gray-600 mt-1">{stepCount}/4 steps</div>
                </button>
              );
            })}
          </div>

          {/* Active shot detail */}
          <div className="xl:col-span-3 space-y-6">
            {activeShot && (
              <>
                {/* Shot Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Left block: Description editor */}
                  <div className="md:col-span-2 card p-5 space-y-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/20 flex items-center justify-center text-lg shrink-0">
                          🎬
                        </div>
                        <div>
                          <h2 className="text-base font-bold text-white">
                            Shot {activeShot.order_index + 1} Editor
                          </h2>
                          <span className="badge bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[9px] mt-0.5 capitalize">
                            {activeShot.shot_type}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={() => {
                          if (confirm('Delete this shot?')) delMut.mutate(activeShot.id);
                        }}
                        className="text-gray-500 hover:text-red-400 transition-colors p-1 rounded-lg hover:bg-red-500/10"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
                    </div>

                    <div>
                      <label className="text-[10px] text-gray-500 block mb-1 font-medium">Shot Prompt/Description (Vietnamese)</label>
                      <textarea
                        value={shotDesc}
                        onChange={(e) => setShotDesc(e.target.value)}
                        rows={4}
                        className="input-field resize-none leading-relaxed text-xs"
                        placeholder="Mô tả bối cảnh diễn ra trong shot này..."
                      />
                      {hasDescChanges && (
                        <button
                          onClick={() => updateShotMut.mutate(shotDesc)}
                          disabled={updateShotMut.isPending}
                          className="btn-primary py-1 px-3 mt-2 text-xs"
                        >
                          {updateShotMut.isPending ? 'Saving...' : 'Save Description'}
                        </button>
                      )}
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 text-[10px] pt-2">
                      <div className="bg-surface-700 rounded-lg p-2">
                        <span className="text-gray-600 block">Camera Framing</span>
                        <span className="text-gray-300 font-medium capitalize">{activeShot.camera?.framing || 'Medium'}</span>
                        <span className="text-gray-500 block text-[9px]">{activeShot.camera?.angle || 'Eye-level'}</span>
                      </div>
                      <div className="bg-surface-700 rounded-lg p-2">
                        <span className="text-gray-600 block">Movement</span>
                        <span className="text-gray-300 font-medium capitalize">{activeShot.camera?.movement || 'Static'}</span>
                      </div>
                      <div className="bg-surface-700 rounded-lg p-2">
                        <span className="text-gray-600 block">Animation Style</span>
                        <span className="text-gray-300 font-medium">{activeShot.motion?.animation_style || 'Live2D'}</span>
                      </div>
                      <div className="bg-surface-700 rounded-lg p-2">
                        <span className="text-gray-600 block">Framerate</span>
                        <span className="text-gray-300 font-medium">{activeShot.motion?.fps || 24} FPS</span>
                      </div>
                    </div>
                  </div>

                  {/* Right block: High-res Keyframe Preview Card */}
                  <div className="md:col-span-1 card p-5 flex flex-col justify-between">
                    <div>
                      <h3 className="text-xs font-semibold text-white mb-2">Keyframe Output</h3>
                      <div className="relative w-full aspect-[2/3] rounded-xl bg-surface-800 border border-accent-500/10 overflow-hidden flex items-center justify-center">
                        {activeShot.keyframe_asset_id ? (
                          <img
                            src={getAssetDownloadUrl(activeShot.keyframe_asset_id)}
                            alt="Generated Keyframe"
                            className="w-full h-full object-cover"
                          />
                        ) : activeShot.background_asset_id ? (
                          <div className="flex flex-col items-center gap-2 text-center text-gray-500">
                            <img
                              src={getAssetDownloadUrl(activeShot.background_asset_id)}
                              alt="Generated Background"
                              className="w-full h-full object-cover opacity-50 absolute inset-0"
                            />
                            <span className="relative z-10 text-[10px] bg-black/60 py-1 px-2 rounded">BG Ready, KF Pending</span>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center gap-2 text-gray-500 text-center p-4">
                            <span className="text-3xl">🖼️</span>
                            <span className="text-[10px]">No assets generated yet</span>
                          </div>
                        )}
                        
                        {loadingKey && (
                          <div className="absolute inset-0 bg-black/75 flex flex-col items-center justify-center gap-2 backdrop-blur-sm z-10">
                            <div className="w-8 h-8 border-3 border-accent-500/20 border-t-accent-500 rounded-full animate-spin" />
                            <span className="text-[10px] text-accent-300 font-semibold animate-pulse">Running AI pipeline...</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {activeShot.generation_prompt && (
                      <div className="mt-3">
                        <span className="text-[9px] text-gray-500 block mb-1 font-medium">Translated AI Prompt</span>
                        <p className="text-[9px] text-gray-400 font-mono line-clamp-2 leading-relaxed bg-surface-850 p-2 rounded border border-accent-500/5 select-all">
                          {activeShot.generation_prompt}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Generation Pipeline */}
                <GenerationPanel
                  steps={GENERATION_STEPS.map((step) => ({
                    ...step,
                    status:
                      step.id === 'background'
                        ? activeShot.background_asset_id ? 'completed' : 'idle'
                        : step.id === 'keyframe'
                        ? activeShot.keyframe_asset_id ? 'completed' : activeShot.background_asset_id ? 'idle' : 'pending'
                        : step.id === 'audio'
                        ? activeShot.audio_asset_id ? 'completed' : activeShot.keyframe_asset_id ? 'idle' : 'pending'
                        : step.id === 'lipsync'
                        ? activeShot.video_export_id ? 'completed' : activeShot.audio_asset_id ? 'idle' : 'pending'
                        : 'idle',
                  }))}
                  currentStep={
                    !activeShot.background_asset_id
                      ? 'background'
                      : !activeShot.keyframe_asset_id
                      ? 'keyframe'
                      : !activeShot.audio_asset_id
                      ? 'audio'
                      : 'lipsync'
                  }
                  onStepClick={(stepId) => {
                    if (stepId === 'background') doGen(activeShot.id, generateBackground, `bg-${activeShot.id}`);
                    else if (stepId === 'keyframe') doGen(activeShot.id, generateKeyframe, `kf-${activeShot.id}`);
                    else if (stepId === 'audio') doGen(activeShot.id, generateAudio, `audio-${activeShot.id}`);
                    else if (stepId === 'lipsync') doGen(activeShot.id, generateLipSync, `ls-${activeShot.id}`);
                  }}
                />
              </>
            )}

            {/* Active Jobs */}
            {jobs && jobs.length > 0 && (
              <div className="card p-4 border-violet-500/20">
                <h3 className="text-xs font-semibold text-violet-400 mb-3 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
                  Active Jobs
                </h3>
                <div className="space-y-2">
                  {jobs.filter((j: any) => j.status === 'in_progress' || j.status === 'pending').slice(0, 5).map((job: any) => (
                    <div key={job.id} className="flex items-center gap-3">
                      <span className="text-[10px] text-gray-400 w-20 truncate">{job.job_type}</span>
                      <div className="flex-1 bg-surface-700 rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full bg-gradient-to-r from-violet-500 to-purple-500 transition-all duration-500"
                          style={{ width: `${Math.round((job.progress || 0) * 100)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-gray-500 w-8 text-right font-mono">{Math.round((job.progress || 0) * 100)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="text-center py-20">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/10 flex items-center justify-center">
            <span className="text-2xl">🎬</span>
          </div>
          <p className="text-gray-400 font-medium">No shots yet</p>
          <p className="text-sm text-gray-600 mt-1">Add a shot to start building this scene.</p>
          <button onClick={() => createMut.mutate()} disabled={createMut.isPending} className="btn-primary mt-4">
            Add First Shot
          </button>
        </div>
      )}
    </div>
  );
}
