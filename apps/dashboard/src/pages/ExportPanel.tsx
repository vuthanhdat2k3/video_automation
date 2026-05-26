import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getTimeline, exportScene, exportProject, getAssetDownloadUrl } from '../api/endpoints';
import { useJobProgress } from '../hooks/useJobProgress';
import { useState, useEffect } from 'react';

export default function ExportPanel() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [exporting, setExporting] = useState<string | null>(null);
  const [projectExporting, setProjectExporting] = useState(false);

  const { data: items, isLoading } = useQuery({
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

  if (isLoading) return <div className="text-gray-400">Loading...</div>;

  const isReady = (shots: any[]) =>
    shots.every((s) => s.background_asset_id && s.keyframe_asset_id && s.audio_asset_id);

  // Find completed export jobs for download links
  const sceneExports = items?.map((item: any) => {
    const scene = item.scene;
    const sceneJobs = (jobs || []).filter(
      (j: any) => j.job_type === 'export' && j.status === 'completed'
    );
    // Match export jobs to scenes by looking at input_data
    const doneJob = sceneJobs.find((j: any) => j.input_data?.scene_id === scene.id);
    const assetId = doneJob?.output_data?.asset_id;
    return { sceneId: scene.id, assetId };
  }) || [];

  const completedExportAssetIds = sceneExports
    .filter((e) => e.assetId)
    .map((e) => e.assetId);

  // Check if a project-level export is completed
  const concatJobs = (jobs || []).filter(
    (j: any) => j.job_type === 'export' && j.status === 'completed'
  );
  const concatJob = concatJobs.find((j: any) => j.input_data?.task_name === 'run_concat_project');
  const projectAssetId = concatJob?.output_data?.asset_id;

  // Active export jobs for progress
  const activeExportJobs = (jobs || []).filter(
    (j: any) => j.job_type === 'export' && (j.status === 'in_progress' || j.status === 'pending')
  );

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Export</h1>

        {/* Project-level export button */}
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
          disabled={projectExporting || !items?.length}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded font-medium text-sm disabled:opacity-50"
        >
          {projectExporting ? 'Exporting...' : 'Export All Scenes (Concat)'}
        </button>
      </div>

      {/* Active export progress indicators */}
      {activeExportJobs.length > 0 && (
        <div className="mb-4 bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-indigo-300 mb-2">
            {activeExportJobs.length} export(s) in progress...
          </h3>
          {activeExportJobs.slice(0, 5).map((job: any) => (
            <div key={job.id} className="flex items-center gap-3 mb-2">
              <span className="text-xs text-gray-400 w-24 truncate">
                {job.task_name || job.job_type}
              </span>
              <div className="flex-1 bg-gray-700 rounded-full h-2">
                <div
                  className="bg-indigo-500 h-2 rounded-full transition-all"
                  style={{ width: `${Math.round((job.progress || 0) * 100)}%` }}
                />
              </div>
              <span className="text-xs text-gray-400 w-10 text-right">
                {Math.round((job.progress || 0) * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Project-level download link */}
      {projectAssetId && (
        <div className="mb-4 bg-green-900/40 rounded-lg p-4 border border-green-700">
          <div className="flex items-center justify-between">
            <span className="text-green-300 font-semibold">
              ✓ Project export ready
            </span>
            <a
              href={getAssetDownloadUrl(projectAssetId)}
              download
              className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded text-sm font-medium"
            >
              Download Final MP4
            </a>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {items?.map((item: any) => {
          const scene = item.scene;
          const shots = item.shots;
          const ready = isReady(shots);
          const bgCount = shots.filter((s: any) => s.background_asset_id).length;
          const kfCount = shots.filter((s: any) => s.keyframe_asset_id).length;
          const audioCount = shots.filter((s: any) => s.audio_asset_id).length;
          const total = shots.length;

          // Find download link for this scene
          const sceneExport = sceneExports.find((e) => e.sceneId === scene.id);
          const downloadUrl = sceneExport?.assetId
            ? getAssetDownloadUrl(sceneExport.assetId)
            : null;

          return (
            <div
              key={scene.id}
              className="bg-gray-800 rounded-lg p-4 border border-gray-700"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">
                    {scene.title || `Scene ${scene.order_index + 1}`}
                  </h3>
                  <div className="flex gap-4 mt-1 text-xs">
                    <span className={bgCount === total ? 'text-green-400' : 'text-gray-500'}>
                      BG {bgCount}/{total}
                    </span>
                    <span className={kfCount === total ? 'text-green-400' : 'text-gray-500'}>
                      KF {kfCount}/{total}
                    </span>
                    <span className={audioCount === total ? 'text-green-400' : 'text-gray-500'}>
                      Audio {audioCount}/{total}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  {downloadUrl ? (
                    <a
                      href={downloadUrl}
                      download
                      className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded font-medium text-sm"
                    >
                      Download MP4
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
                      className={`px-4 py-2 rounded font-medium text-sm disabled:opacity-50 ${
                        ready
                          ? 'bg-green-600 hover:bg-green-500'
                          : 'bg-gray-700 text-gray-400'
                      }`}
                    >
                      {exporting === scene.id
                        ? 'Exporting...'
                        : ready
                        ? 'Export MP4'
                        : 'Incomplete'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {items?.length === 0 && (
        <p className="text-gray-500 text-center py-12">No scenes to export.</p>
      )}
    </div>
  );
}
