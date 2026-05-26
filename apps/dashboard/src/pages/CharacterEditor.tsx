import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCharacters, updateCharacter } from '../api/endpoints';
import { useState, useEffect } from 'react';

export default function CharacterEditor() {
  const { id, cid } = useParams<{ id: string; cid: string }>();
  const qc = useQueryClient();

  const { data: chars } = useQuery({
    queryKey: ['characters', id],
    queryFn: () => getCharacters(id!),
    enabled: !!id,
  });

  const character = chars?.find((c: any) => c.id === cid);

  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (character) {
      setName(character.name || '');
      setRole(character.role || '');
      setDescription(character.description || '');
    }
  }, [character]);

  const updateMut = useMutation({
    mutationFn: (data: any) => updateCharacter(cid!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['characters', id] });
    },
  });

  if (!character) return <div className="text-gray-400">Loading...</div>;

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold">Edit Character</h1>
      <div className="bg-gray-800 rounded-lg p-4 space-y-3">
        <div>
          <label className="text-sm text-gray-400 block mb-1">Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-indigo-500 outline-none"
          />
        </div>
        <div>
          <label className="text-sm text-gray-400 block mb-1">Role</label>
          <input
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-indigo-500 outline-none"
          />
        </div>
        <div>
          <label className="text-sm text-gray-400 block mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-indigo-500 outline-none resize-none"
          />
        </div>
        <button
          onClick={() => updateMut.mutate({ name, role, description })}
          disabled={updateMut.isPending}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded font-medium text-sm disabled:opacity-50"
        >
          {updateMut.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
      {character.prompt && (
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="font-semibold mb-2 text-sm text-gray-400">Generation Prompt</h3>
          <pre className="text-sm text-gray-300 whitespace-pre-wrap">{character.prompt}</pre>
        </div>
      )}
    </div>
  );
}
