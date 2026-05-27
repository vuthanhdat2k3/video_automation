import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCharacters, deleteCharacter, getAssetDownloadUrl } from '../api/endpoints';

const ROLE_COLORS: Record<string, string> = {
  protagonist: 'from-blue-500 to-cyan-500',
  deuteragonist: 'from-emerald-500 to-teal-500',
  antagonist: 'from-red-500 to-rose-500',
  supporting: 'from-violet-500 to-purple-500',
  minor: 'from-gray-400 to-gray-500',
};

const ROLE_ICONS: Record<string, string> = {
  protagonist: '⭐',
  deuteragonist: '🌟',
  antagonist: '💀',
  supporting: '👥',
  minor: '▪️',
};

export default function CharacterGallery() {
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-500/30 border-t-accent-500 rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading characters...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Character Gallery</h1>
          <p className="text-sm text-gray-500 mt-1">
            {chars?.length || 0} character{(chars?.length || 0) !== 1 ? 's' : ''} in this project
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {chars?.map((c: any) => {
          const roleLower = (c.role || 'supporting').toLowerCase();
          const grad = ROLE_COLORS[roleLower] || ROLE_COLORS.supporting;
          const icon = ROLE_ICONS[roleLower] || '👤';

          return (
            <Link
              key={c.id}
              to={`/projects/${id}/characters/${c.id}`}
              className="card group overflow-hidden"
            >
              {/* Avatar area */}
              <div className="p-5 pb-3">
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 rounded-2xl overflow-hidden shrink-0 shadow-lg border border-accent-500/10">
                    {c.reference_asset_id ? (
                      <img
                        src={getAssetDownloadUrl(c.reference_asset_id)}
                        alt={c.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className={`w-full h-full bg-gradient-to-br ${grad} flex items-center justify-center text-2xl`}>
                        {icon}
                      </div>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-semibold text-white text-base group-hover:text-accent-300 transition-colors truncate">
                      {c.name || 'Unnamed Character'}
                    </h3>
                    <span className={`badge bg-${roleLower === 'protagonist' ? 'blue' : roleLower === 'antagonist' ? 'red' : roleLower === 'deuteragonist' ? 'emerald' : 'violet'}-500/10 text-${roleLower === 'protagonist' ? 'blue' : roleLower === 'antagonist' ? 'red' : roleLower === 'deuteragonist' ? 'emerald' : 'violet'}-400 border border-${roleLower === 'protagonist' ? 'blue' : roleLower === 'antagonist' ? 'red' : roleLower === 'deuteragonist' ? 'emerald' : 'violet'}-500/20 text-[10px]`}>
                      {c.role}
                    </span>
                  </div>
                </div>
              </div>

              {c.description && (
                <div className="px-5 pb-4">
                  <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed">{c.description}</p>
                </div>
              )}

              <div className="px-5 py-2.5 border-t border-accent-500/10 flex items-center justify-between">
                <span className="text-[10px] text-gray-600">
                  {c.prompt ? '✓ Generated' : 'No prompt'}
                </span>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (confirm(`Delete "${c.name}"?`)) delMut.mutate(c.id);
                  }}
                  className="text-gray-600 hover:text-red-400 transition-colors p-1 rounded hover:bg-red-500/10 text-xs"
                >
                  Delete
                </button>
              </div>
            </Link>
          );
        })}
      </div>

      {(!chars || chars.length === 0) && (
        <div className="text-center py-20">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/10 flex items-center justify-center">
            <span className="text-2xl">👤</span>
          </div>
          <p className="text-gray-400 font-medium">No characters yet</p>
          <p className="text-sm text-gray-600 mt-1">Materialize the story first to auto-generate characters.</p>
        </div>
      )}
    </div>
  );
}
