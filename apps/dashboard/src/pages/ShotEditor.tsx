import { useParams, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getShots,
  createShot,
  deleteShot,
  generateBackground,
  generateKeyframe,
  generateAudio,
  exportScene,
} from '../api/endpoints';
import GenerationPanel from '../components/GenerationPanel';
import { useState } from 'react';

export default function ShotEditor() {
  const { sid } = useParams<{ sid: string }>();
  const [searchParams] = useSearchParams();
  const qc = useQueryClient();
  const [loading, setLoading] = useState<string | null>(null);

  const { data: shots, isLoading } = useQuery({
    queryKey: ['shots', sid],
    queryFn: () => getShots(sid!),
    enabled: !!sid,
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

  const doGen = async (
    shotId: string,
    fn: (id: string) => Promise<any>,
    key: string
  ) => {
    setLoading(key);
    try {
      await fn(shotId);
      qc.invalidateQueries({ queryKey: ['shots', sid] });
    } finally {
      setLoading(null);
    }
  };

  const exportMut = useMutation({
    mutationFn: () => exportScene(sid!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shots', sid] });
    },
  });

  if (isLoading) return <div className="text-gray-400">Loading shots...</div>;

  const allBg = (shots || []).every((s: any) => s.background_asset_id);
  const allKf = (shots || []).every((s: any) => s.keyframe_asset_id);
  const allAudio = (shots || []).every((s: any) => s.audio_asset_id);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Shot Editor</h1>
        <div className="flex gap-2">
          {(shots || []).length > 0 && allBg && allKf && allAudio && (
            <button
              onClick={() => exportMut.mutate()}
              disabled={exportMut.isPending}
              className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded font-medium text-sm disabled:opacity-50"
            >
              {exportMut.isPending ? 'Exporting...' : 'Export Scene'}
            </button>
          )}
          <button
            onClick={() => createMut.mutate()}
            disabled={createMut.isPending}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded font-medium text-sm disabled:opacity-50"
          >
            + Add Shot
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {shots?.map((shot: any) => (
          <div
            key={shot.id}
            className={`bg-gray-800 rounded-lg p-4 border border-gray-700 ${
              searchParams.get('shot') === shot.id
                ? 'ring-2 ring-indigo-500'
                : ''
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold">
                  Shot {shot.order_index + 1} · {shot.shot_type}
                </h3>
                <p className="text-sm text-gray-400 mt-1">
                  {shot.description || shot.generation_prompt || '(empty)'}
                </p>
                <div className="flex gap-2 mt-1 text-xs text-gray-500">
                  <span>{shot.duration_seconds}s</span>
                  <span>{shot.camera?.framing || 'medium'} · {shot.camera?.angle || 'eye-level'}</span>
                  <span>{shot.motion?.animation_style || 'live2d'}</span>
                </div>
              </div>
              <button
                onClick={() => {
                  if (confirm('Delete shot?')) delMut.mutate(shot.id);
                }}
                className="text-red-400 hover:text-red-300 text-sm"
              >
                Delete
              </button>
            </div>
            <GenerationPanel
              hasBackground={!!shot.background_asset_id}
              hasKeyframe={!!shot.keyframe_asset_id}
              hasAudio={!!shot.audio_asset_id}
              onGenerateBackground={() =>
                doGen(shot.id, generateBackground, `bg-${shot.id}`)
              }
              onGenerateKeyframe={() =>
                doGen(shot.id, generateKeyframe, `kf-${shot.id}`)
              }
              onGenerateAudio={() =>
                doGen(shot.id, generateAudio, `audio-${shot.id}`)
              }
              loading={loading}
            />
          </div>
        ))}
      </div>

      {shots?.length === 0 && (
        <p className="text-gray-500 text-center py-12">
          No shots yet. Add one to get started.
        </p>
      )}
    </div>
  );
}
