import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTimeline, generateAllKeyframes, generateAllAudio } from '../api/endpoints';
import { useJobProgress } from '../hooks/useJobProgress';
import { useEffect } from 'react';

export default function PipelineTimeline() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: timelineData, isLoading } = useQuery({
    queryKey: ['timeline', id],
    queryFn: () => getTimeline(id!),
    enabled: !!id,
  });

  const { jobs } = useJobProgress(id);

  useEffect(() => {
    if (jobs?.length) {
      qc.invalidateQueries({ queryKey: ['timeline', id] });
    }
  }, [jobs, id, qc]);

  const kfMut = useMutation({
    mutationFn: (sceneId: string) => generateAllKeyframes(sceneId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['timeline', id] }),
  });

  const audioMut = useMutation({
    mutationFn: (sceneId: string) => generateAllAudio(sceneId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['timeline', id] }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-500/30 border-t-accent-500 rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading timeline...</p>
        </div>
      </div>
    );
  }

  const scenes = timelineData?.scenes || [];
  const totalShots = scenes.reduce((acc: number, i: any) => acc + i.shots.length, 0) || 0;
  const activeJobs = (jobs || []).filter(
    (j: any) => j.status === 'in_progress' || j.status === 'pending'
  );

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Pipeline Timeline</h1>
          <p className="text-sm text-gray-500 mt-1">
            {scenes.length} scenes · {totalShots} shots
            {activeJobs.length > 0 && (
              <span className="ml-2 text-amber-400">· ⚡ {activeJobs.length} active job{activeJobs.length > 1 ? 's' : ''}</span>
            )}
          </p>
        </div>
        <span className="text-xs text-gray-500">
          {scenes.reduce((acc: number, i: any) => acc + i.shots.filter((s: any) => s.keyframe_asset_id).length, 0) || 0}/{totalShots} keyframes
          {' · '}
          {scenes.reduce((acc: number, i: any) => acc + i.shots.filter((s: any) => s.audio_asset_id).length, 0) || 0}/{totalShots} audio
        </span>
      </div>

      {/* Active Jobs */}
      {activeJobs.length > 0 && (
        <div className="card p-4 border-amber-500/20">
          <h3 className="text-xs font-semibold text-amber-400 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            Generation Progress
          </h3>
          <div className="space-y-2">
            {activeJobs.slice(0, 8).map((job: any) => (
              <div key={job.id} className="flex items-center gap-3">
                <span className="text-[10px] text-gray-400 w-20 truncate">{job.job_type || job.type}</span>
                <div className="flex-1 bg-surface-700 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-500"
                    style={{ width: `${Math.round((job.progress || 0) * 100)}%` }}
                  />
                </div>
                <span className="text-[10px] text-gray-500 w-8 text-right font-mono">
                  {Math.round((job.progress || 0) * 100)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scenes */}
      <div className="space-y-4">
        {scenes.map((item: any, sceneIdx: number) => {
          const scene = item.scene;
          const shots = item.shots;
          const totalDur = shots.reduce((acc: number, s: any) => acc + (s.duration_seconds || 4), 0);
          const bgDone = shots.filter((s: any) => s.background_asset_id).length;
          const kfDone = shots.filter((s: any) => s.keyframe_asset_id).length;
          const audioDone = shots.filter((s: any) => s.audio_asset_id).length;
          const allReady = bgDone === shots.length && kfDone === shots.length && audioDone === shots.length;
          const progress = shots.length > 0 ? Math.round(((bgDone + kfDone + audioDone) / (shots.length * 3)) * 100) : 0;

          return (
            <div key={scene.id} className="card overflow-hidden animate-slide-up" style={{ animationDelay: `${sceneIdx * 80}ms` }}>
              {/* Scene header */}
              <div className="p-4 border-b border-accent-500/10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold shrink-0 ${
                      allReady
                        ? 'bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/20'
                        : 'bg-surface-700 text-gray-400'
                    }`}>
                      {sceneIdx + 1}
                    </div>
                    <div className="min-w-0">
                      <button
                        onClick={() => navigate(`/projects/${id}/scenes/${scene.id}`)}
                        className="font-semibold text-white text-sm hover:text-accent-300 transition-colors truncate block"
                      >
                        {scene.title || `Scene ${scene.order_index + 1}`}
                      </button>
                      <p className="text-[10px] text-gray-500">
                        Ep {scene.episode_number || '?'} · {shots.length} shot{shots.length !== 1 ? 's' : ''} · {totalDur.toFixed(0)}s total
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* Progress ring */}
                    <div className="flex items-center gap-1.5 text-[10px]">
                      <span className={bgDone === shots.length ? 'text-emerald-400' : 'text-gray-600'}>
                        🖼️ {bgDone}/{shots.length}
                      </span>
                      <span className={kfDone === shots.length ? 'text-blue-400' : 'text-gray-600'}>
                        🎨 {kfDone}/{shots.length}
                      </span>
                      <span className={audioDone === shots.length ? 'text-violet-400' : 'text-gray-600'}>
                        🎵 {audioDone}/{shots.length}
                      </span>
                    </div>
                    <button
                      onClick={() => kfMut.mutate(scene.id)}
                      disabled={kfMut.isPending}
                      className="btn-secondary text-[11px] px-2 py-1"
                      title="Generate all keyframes"
                    >
                      🎨
                    </button>
                    <button
                      onClick={() => audioMut.mutate(scene.id)}
                      disabled={audioMut.isPending}
                      className="btn-secondary text-[11px] px-2 py-1"
                      title="Generate all audio"
                    >
                      🎵
                    </button>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mt-3 flex items-center gap-3">
                  <div className="flex-1 bg-surface-700 rounded-full h-1">
                    <div
                      className="h-1 rounded-full bg-gradient-to-r from-accent-500 to-purple-500 transition-all duration-500"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-gray-500 font-mono w-8 text-right">{progress}%</span>
                </div>
              </div>

              {/* Shots strip */}
              <div className="overflow-x-auto">
                <div className="flex gap-3 p-4 min-w-max">
                  {shots.map((shot: any) => {
                    const isReady = shot.background_asset_id && shot.keyframe_asset_id && shot.audio_asset_id;
                    return (
                      <button
                        key={shot.id}
                        onClick={() => navigate(`/projects/${id}/scenes/${scene.id}?shot=${shot.id}`)}
                        className={`w-36 shrink-0 rounded-xl border p-3 transition-all text-left group ${
                          isReady
                            ? 'bg-emerald-500/5 border-emerald-500/20 hover:border-emerald-500/40'
                            : 'bg-surface-800 border-surface-600 hover:border-accent-500/30'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-semibold text-white">
                            Shot {shot.order_index + 1}
                          </span>
                          <span className="text-[10px] text-gray-500">{shot.duration_seconds}s</span>
                        </div>

                        {/* Shot preview placeholder */}
                        <div className={`w-full aspect-[9/16] rounded-lg mb-2 flex items-center justify-center text-lg transition-all ${
                          shot.keyframe_asset_id
                            ? 'bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20'
                            : 'bg-deep-800 border border-surface-600'
                        }`}>
                          {shot.keyframe_asset_id ? '🎨' : shot.background_asset_id ? '🖼️' : '⬜'}
                        </div>

                        {/* Status badges */}
                        <div className="flex gap-1 flex-wrap">
                          {shot.background_asset_id ? (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">BG</span>
                          ) : (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-700 text-gray-600">BG</span>
                          )}
                          {shot.keyframe_asset_id ? (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">KF</span>
                          ) : (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-700 text-gray-600">KF</span>
                          )}
                          {shot.audio_asset_id ? (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400">AUD</span>
                          ) : (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-surface-700 text-gray-600">AUD</span>
                          )}
                          {shot.video_export_id && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400">VID</span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {(!scenes || scenes.length === 0) && (
        <div className="text-center py-20">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-violet-500/20 to-purple-500/20 border border-violet-500/10 flex items-center justify-center">
            <span className="text-2xl">🎬</span>
          </div>
          <p className="text-gray-400 font-medium">No scenes yet</p>
          <p className="text-sm text-gray-600 mt-1">Materialize the story to create scenes and shots.</p>
        </div>
      )}
    </div>
  );
}
