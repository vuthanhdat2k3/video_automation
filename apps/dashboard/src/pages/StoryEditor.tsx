import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getStory,
  generateStory,
  regenerateStory,
  materializeStory,
} from '../api/endpoints';

export default function StoryEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: bible, isLoading, isError } = useQuery({
    queryKey: ['story', id],
    queryFn: () => getStory(id!),
    enabled: !!id,
    retry: false,
  });

  const genMut = useMutation({
    mutationFn: () => generateStory(id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['story', id] }),
  });

  const regenMut = useMutation({
    mutationFn: () => regenerateStory(id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['story', id] }),
  });

  const matMut = useMutation({
    mutationFn: () => materializeStory(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['story', id] });
      navigate(`/projects/${id}/timeline`);
    },
  });

  if (isLoading) return <div className="text-gray-400">Loading story bible...</div>;

  const noStory = isError || !bible;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Story Bible</h1>
        <div className="flex gap-2">
          {noStory ? (
            <button
              onClick={() => genMut.mutate()}
              disabled={genMut.isPending}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded font-medium text-sm disabled:opacity-50"
            >
              {genMut.isPending ? 'Generating...' : 'Generate Story'}
            </button>
          ) : (
            <>
              <button
                onClick={() => regenMut.mutate()}
                disabled={regenMut.isPending}
                className="px-4 py-2 bg-yellow-600 hover:bg-yellow-500 rounded font-medium text-sm disabled:opacity-50"
              >
                Regenerate
              </button>
              <button
                onClick={() => matMut.mutate()}
                disabled={matMut.isPending}
                className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded font-medium text-sm disabled:opacity-50"
              >
                {matMut.isPending ? 'Materializing...' : 'Materialize'}
              </button>
            </>
          )}
        </div>
      </div>

      {noStory ? (
        <div className="text-gray-500 text-center py-12">
          <p className="text-lg mb-2">No story bible yet</p>
          <p className="text-sm">Click "Generate Story" to create one from the project prompt</p>
        </div>
      ) : (
        <>
          <div className="bg-gray-800 rounded-lg p-4 space-y-2">
            <h2 className="font-bold text-lg">{bible.series_name}</h2>
            <p className="text-gray-300 text-sm">{bible.series_overview}</p>
            <div className="flex gap-2 mt-2">
              <span className="px-2 py-0.5 bg-gray-700 text-xs rounded">{bible.target_audience}</span>
              <span className="px-2 py-0.5 bg-gray-700 text-xs rounded">{bible.total_episodes} episodes</span>
            </div>
            <div className="flex gap-1 flex-wrap mt-1">
              {bible.genre?.map((g: string) => (
                <span key={g} className="px-2 py-0.5 bg-indigo-900 text-indigo-200 text-xs rounded">{g}</span>
              ))}
            </div>
          </div>

          <h2 className="font-bold text-lg mt-4">Characters</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {bible.characters?.map((c: any) => (
              <div key={c.name} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                <h3 className="font-semibold">{c.name}</h3>
                <span className="text-xs text-gray-400">{c.role}</span>
                <p className="text-sm text-gray-300 mt-1">{c.personality}</p>
              </div>
            ))}
          </div>

          <h2 className="font-bold text-lg mt-4">Episodes</h2>
          <div className="space-y-3">
            {bible.episodes?.map((ep: any) => (
              <div key={ep.number} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
                <h3 className="font-semibold">Ep {ep.number}: {ep.title}</h3>
                <p className="text-sm text-gray-300 mt-1">{ep.summary}</p>
                <p className="text-xs text-gray-500 mt-1">{ep.scenes?.length || 0} scenes</p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
