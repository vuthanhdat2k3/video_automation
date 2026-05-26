import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCharacters, deleteCharacter } from '../api/endpoints';

export default function CharacterList() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const { data: chars, isLoading } = useQuery({
    queryKey: ['characters', id],
    queryFn: () => getCharacters(id!),
    enabled: !!id,
  });

  const delMut = useMutation({
    mutationFn: (cid: string) => deleteCharacter(cid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['characters', id] }),
  });

  if (isLoading) return <div className="text-gray-400">Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Characters</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {chars?.map((c: any) => (
          <div
            key={c.id}
            className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-indigo-500 transition-colors"
          >
            <div className="flex items-start justify-between">
              <Link
                to={`/projects/${id}/characters/${c.id}`}
                className="font-semibold text-lg hover:text-indigo-400"
              >
                {c.name || 'Unnamed'}
              </Link>
              <button
                onClick={() => {
                  if (confirm('Delete character?')) delMut.mutate(c.id);
                }}
                className="text-red-400 hover:text-red-300 text-sm"
              >
                Delete
              </button>
            </div>
            <span className="text-xs px-2 py-0.5 bg-gray-700 rounded mt-1 inline-block">
              {c.role}
            </span>
            {c.description && (
              <p className="text-sm text-gray-400 mt-2 line-clamp-2">{c.description}</p>
            )}
          </div>
        ))}
      </div>
      {chars?.length === 0 && (
        <p className="text-gray-500 text-center py-12">No characters yet. Materialize the story first.</p>
      )}
    </div>
  );
}
