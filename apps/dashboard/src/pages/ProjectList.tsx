import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProjects, createProject, deleteProject } from '../api/endpoints';
import type { Project } from '../types';

const styles = [
  { value: '2d_anime', label: 'Anime' },
  { value: '2d_chinese_donghua', label: 'Donghua' },
  { value: '2d_manga', label: 'Manga' },
  { value: '2d_realistic', label: 'Realistic' },
];
const ratios = ['9:16', '16:9', '4:3', '1:1'];

export default function ProjectList() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [style, setStyle] = useState('2d_anime');
  const [aspect, setAspect] = useState('9:16');

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  });

  const createMut = useMutation({
    mutationFn: () => createProject({ name, style, aspect_ratio: aspect } as any),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ['projects'] });
      setShowForm(false);
      setName('');
      navigate(`/projects/${p.id}/story`);
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });

  const styleLabel = (v: string) => styles.find((s) => s.value === v)?.label || v;

  if (isLoading) return <div className="text-gray-400">Loading projects...</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded font-medium text-sm"
        >
          + New Project
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-800 rounded-lg p-4 mb-6 space-y-3">
          <input
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-indigo-500 outline-none"
            autoFocus
          />
          <div className="flex gap-4">
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="px-3 py-2 bg-gray-700 rounded border border-gray-600"
            >
              {styles.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <select
              value={aspect}
              onChange={(e) => setAspect(e.target.value)}
              className="px-3 py-2 bg-gray-700 rounded border border-gray-600"
            >
              {ratios.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => createMut.mutate()}
              disabled={!name.trim() || createMut.isPending}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded font-medium text-sm disabled:opacity-50"
            >
              {createMut.isPending ? 'Creating...' : 'Create'}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {projects?.map((p: Project) => (
          <div
            key={p.id}
            className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-indigo-500 transition-colors cursor-pointer group"
            onClick={() => navigate(`/projects/${p.id}/story`)}
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-lg">{p.name}</h3>
                <div className="flex gap-2 mt-1">
                  <span className="px-2 py-0.5 bg-gray-700 text-xs rounded">
                    {styleLabel(p.style)}
                  </span>
                  <span className="px-2 py-0.5 bg-gray-700 text-xs rounded">
                    {p.aspect_ratio}
                  </span>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm('Delete this project?')) deleteMut.mutate(p.id);
                }}
                className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 text-sm"
              >
                Delete
              </button>
            </div>
            <div className="mt-2 text-xs text-gray-500">
              Created {new Date(p.created_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
