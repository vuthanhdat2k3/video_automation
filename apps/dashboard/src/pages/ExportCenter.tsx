import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getTimeline, exportScene, exportProject, getAssetDownloadUrl } from '../api/endpoints';
import { useJobProgress } from '../hooks/useJobProgress';
import { useState, useEffect } from 'react';

export default function ExportCenter() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [exporting, setExporting] = useState<string | null>(null);
  const [projectExporting, setProjectExporting] = useState(false);

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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-500/30 border-t-accent-500 rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  const isReady = (shots: any[]) =>
    shots.every((s) => s.background_asset_id && s.keyframe_asset_id && s.audio_asset_id);

  const scenes = timelineData?.scenes || [];
  const sceneExports: { sceneId: string; assetId: string | null }[] =
    scenes.map((item: any) => {
      const scene = item.scene;
      const doneJob = (jobs || []).find(
        (j: any) => j.job_type?.includes('export') && j.status === 'completed' && j.input_data?.scene_id === scene.id
      );
      const od = doneJob?.output_data as Record<string, unknown> | undefined;
      return { sceneId: scene.id, assetId: (od?.asset_id as string) || null };
    }) || [];

  const concatJob = (jobs || []).find(
    (j: any) => j.status === 'completed' && (j.input_data as Record<string, unknown> | undefined)?.task_name === 'run_concat_project'
  );
  const concatOutputData = concatJob?.output_data as Record<string, unknown> | undefined;
  const projectAssetId = (concatOutputData?.asset_id as string) || null;

  const activeExportJobs = (jobs || []).filter(
    (j: any) => (j.job_type?.includes('export')) && (j.status === 'in_progress' || j.status === 'pending')
  );

  const totalScenes = scenes.length || 0;
  const readyScenes = scenes.filter((i: any) => isReady(i.shots)).length || 0;
  const exportedScenes = sceneExports.filter((e) => e.assetId).length;

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Export Center</h1>
          <p className="text-sm text-gray-500 mt-1">
            {readyScenes}/{totalScenes} scenes ready · {exportedScenes} exported
          </p>
        </div>
        <button
          onClick={async () => {
            setProjectExporting(true);
            try {
              await exportProject(id!);
            } catch (e: any) {
              alert(`Project export failed: ${e.message}`);
            } finally {
              setProjectExporting(false);
            }
          }}
          disabled={projectExporting || !scenes.length}
          className="btn-primary flex items-center gap-2"
        >
          {projectExporting ? (
            <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Exporting All...</>
          ) : (
            <><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 8.25H7.5a2.25 2.25 0 00-2.25 2.25v9a2.25 2.25 0 002.25 2.25h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25H15M12 1.5v12m0 0l-3-3m3 3l3-3" />
            </svg> Export All (Concat)</>
          )}
        </button>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-blue-500/20 flex items-center justify-center">
              🎬
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{totalScenes}</p>
              <p className="text-[10px] text-gray-500">Total Scenes</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/20 flex items-center justify-center">
              ✅
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{readyScenes}</p>
              <p className="text-[10px] text-gray-500">Ready to Export</p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-500/20 border border-violet-500/20 flex items-center justify-center">
              📦
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{exportedScenes}</p>
              <p className="text-[10px] text-gray-500">Exported</p>
            </div>
          </div>
        </div>
      </div>

      {/* Active export progress */}
      {activeExportJobs.length > 0 && (
        <div className="card p-4 border-amber-500/20">
          <h3 className="text-xs font-semibold text-amber-400 mb-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            {activeExportJobs.length} export{activeExportJobs.length > 1 ? 's' : ''} in progress
          </h3>
          <div className="space-y-2">
            {activeExportJobs.slice(0, 5).map((job: any) => (
              <div key={job.id} className="flex items-center gap-3">
                <span className="text-[10px] text-gray-400 w-24 truncate">{job.job_type || 'export'}</span>
                <div className="flex-1 bg-surface-700 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 transition-all duration-500"
                    style={{ width: `${Math.round((job.progress || 0) * 100)}%` }}
                  />
                </div>
                <span className="text-[10px] text-gray-500 w-8 text-right font-mono">{Math.round((job.progress || 0) * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Project-level download */}
      {projectAssetId && (
        <div className="card border-emerald-500/20 p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/20 flex items-center justify-center text-xl">
                🎉
              </div>
              <div>
                <h3 className="text-sm font-semibold text-emerald-400">Full Project Export Ready</h3>
                <p className="text-[10px] text-gray-500">All scenes concatenated into a single video</p>
              </div>
            </div>
            <a
              href={getAssetDownloadUrl(projectAssetId)}
              download
              className="btn-primary flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
              Download MP4
            </a>
          </div>
        </div>
      )}

      {/* Scene list */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-white">Scenes</h3>
        {scenes.map((item: any) => {
          const scene = item.scene;
          const shots = item.shots;
          const ready = isReady(shots);
          const bgCount = shots.filter((s: any) => s.background_asset_id).length;
          const kfCount = shots.filter((s: any) => s.keyframe_asset_id).length;
          const audioCount = shots.filter((s: any) => s.audio_asset_id).length;
          const total = shots.length;

          const sceneExport = sceneExports.find((e) => e.sceneId === scene.id);
          const downloadUrl = sceneExport?.assetId ? getAssetDownloadUrl(sceneExport.assetId) : null;

          return (
            <div key={scene.id} className="card p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold shrink-0 ${
                    ready
                      ? 'bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/20'
                      : 'bg-surface-700 text-gray-400'
                  }`}>
                    {scene.order_index + 1}
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-white text-sm truncate">
                      {scene.title || `Scene ${scene.order_index + 1}`}
                    </h3>
                    <div className="flex gap-3 mt-0.5 text-[10px]">
                      <span className={bgCount === total ? 'text-emerald-400' : 'text-gray-600'}>
                        🖼️ {bgCount}/{total}
                      </span>
                      <span className={kfCount === total ? 'text-blue-400' : 'text-gray-600'}>
                        🎨 {kfCount}/{total}
                      </span>
                      <span className={audioCount === total ? 'text-violet-400' : 'text-gray-600'}>
                        🎵 {audioCount}/{total}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {downloadUrl ? (
                    <a href={downloadUrl} download className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                      </svg>
                      MP4
                    </a>
                  ) : (
                    <button
                      onClick={async () => {
                        setExporting(scene.id);
                        try {
                          await exportScene(scene.id);
                        } catch (e: any) {
                          alert(`Export failed: ${e.message}`);
                        } finally {
                          setExporting(null);
                        }
                      }}
                      disabled={!ready || exporting === scene.id}
                      className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all disabled:opacity-50 ${
                        ready
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20'
                          : 'bg-surface-700 text-gray-500 border border-surface-600'
                      }`}
                    >
                      {exporting === scene.id ? 'Exporting...' : ready ? 'Export' : 'Incomplete'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {(!scenes || scenes.length === 0) && (
        <div className="text-center py-20">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-pink-500/20 to-rose-500/20 border border-pink-500/10 flex items-center justify-center">
            <span className="text-2xl">📦</span>
          </div>
          <p className="text-gray-400 font-medium">No scenes to export</p>
          <p className="text-sm text-gray-600 mt-1">Create scenes and shots first, then come back here to export.</p>
        </div>
      )}
    </div>
  );
}
