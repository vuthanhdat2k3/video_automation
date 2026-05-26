import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getTimeline, exportScene } from '../api/endpoints';
import { useState } from 'react';

export default function ExportPanel() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [exporting, setExporting] = useState<string | null>(null);

  const { data: items, isLoading } = useQuery({
    queryKey: ['timeline', id],
    queryFn: () => getTimeline(id!),
    enabled: !!id,
  });

  if (isLoading) return <div className="text-gray-400">Loading...</div>;

  const isReady = (shots: any[]) =>
    shots.every((s) => s.background_asset_id && s.keyframe_asset_id && s.audio_asset_id);

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Export</h1>

      <div className="space-y-3">
        {items?.map((item: any) => {
          const scene = item.scene;
          const shots = item.shots;
          const ready = isReady(shots);
          const bgCount = shots.filter((s: any) => s.background_asset_id).length;
          const kfCount = shots.filter((s: any) => s.keyframe_asset_id).length;
          const audioCount = shots.filter((s: any) => s.audio_asset_id).length;
          const total = shots.length;

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
                <button
                  onClick={async () => {
                    setExporting(scene.id);
                    try {
                      const result = await exportScene(scene.id);
                      qc.invalidateQueries({ queryKey: ['timeline', id] });
                      alert(`Export complete! Asset ID: ${result.asset_id}`);
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
