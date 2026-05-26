import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTimeline, generateAllKeyframes, generateAllAudio } from '../api/endpoints';

export default function Timeline() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: items, isLoading } = useQuery({
    queryKey: ['timeline', id],
    queryFn: () => getTimeline(id!),
    enabled: !!id,
  });

  const kfMut = useMutation({
    mutationFn: (sceneId: string) => generateAllKeyframes(sceneId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['timeline', id] }),
  });

  const audioMut = useMutation({
    mutationFn: (sceneId: string) => generateAllAudio(sceneId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['timeline', id] }),
  });

  if (isLoading) return <div className="text-gray-400">Loading timeline...</div>;

  const totalShots = items?.reduce((acc: number, i: any) => acc + i.shots.length, 0) || 0;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Timeline</h1>
        <span className="text-sm text-gray-400">
          {items?.length} scenes · {totalShots} shots
        </span>
      </div>

      <div className="space-y-4">
        {items?.map((item: any) => {
          const scene = item.scene;
          const shots = item.shots;
          const totalDur = shots.reduce(
            (acc: number, s: any) => acc + (s.duration_seconds || 4),
            0
          );

          return (
            <div
              key={scene.id}
              className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden"
            >
              <div className="p-4 border-b border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <h3
                      className="font-semibold cursor-pointer hover:text-indigo-400"
                      onClick={() =>
                        navigate(`/projects/${id}/scenes/${scene.id}`)
                      }
                    >
                      {scene.title || `Scene ${scene.order_index + 1}`}
                    </h3>
                    <p className="text-xs text-gray-500">
                      Ep {scene.episode_number || '?'} · {shots.length} shots ·{' '}
                      {totalDur.toFixed(0)}s
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => kfMut.mutate(scene.id)}
                      disabled={kfMut.isPending}
                      className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded disabled:opacity-50"
                    >
                      Generate All Keyframes
                    </button>
                    <button
                      onClick={() => audioMut.mutate(scene.id)}
                      disabled={audioMut.isPending}
                      className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded disabled:opacity-50"
                    >
                      Generate All Audio
                    </button>
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <div className="flex gap-3 p-4 min-w-max">
                  {shots.map((shot: any) => (
                    <div
                      key={shot.id}
                      className="w-40 shrink-0 rounded border p-2 cursor-pointer hover:border-indigo-500 transition-colors bg-gray-800 border-gray-600"
                      onClick={() =>
                        navigate(`/projects/${id}/scenes/${scene.id}?shot=${shot.id}`)
                      }
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium">
                          Shot {shot.order_index + 1}
                        </span>
                        <span className="text-xs text-gray-500">
                          {shot.duration_seconds}s
                        </span>
                      </div>
                      <div className="w-full aspect-[9/16] bg-gray-900 rounded mb-1 flex items-center justify-center text-xs text-gray-600">
                        {shot.keyframe_asset_id ? '🎨' : '⬜'}
                      </div>
                      <div className="flex gap-1 text-[10px]">
                        {shot.background_asset_id && (
                          <span className="px-1 bg-green-900 text-green-300 rounded">
                            BG
                          </span>
                        )}
                        {shot.keyframe_asset_id && (
                          <span className="px-1 bg-blue-900 text-blue-300 rounded">
                            KF
                          </span>
                        )}
                        {shot.audio_asset_id && (
                          <span className="px-1 bg-purple-900 text-purple-300 rounded">
                            Audio
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {items?.length === 0 && (
        <p className="text-gray-500 text-center py-12">
          No scenes yet. Materialize the story first.
        </p>
      )}
    </div>
  );
}
