import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProjects, createProject, deleteProject, updateProject, deleteAllProjects } from '../api/endpoints';
import type { Project } from '../types';

const STYLES = [
  { value: '2d_anime', label: 'Anime', icon: '🌸' },
  { value: '2d_chinese_donghua', label: 'Donghua', icon: '🐉' },
  { value: '2d_manga', label: 'Manga', icon: '📖' },
  { value: '2d_realistic', label: 'Realistic', icon: '🎯' },
];
const RATIOS = ['9:16', '16:9', '4:3', '1:1'];

const STYLE_COLORS: Record<string, string> = {
  '2d_anime': 'from-blue-500 to-violet-600',
  '2d_chinese_donghua': 'from-amber-500 to-red-600',
  '2d_manga': 'from-gray-300 to-gray-500',
  '2d_realistic': 'from-emerald-500 to-teal-600',
};

export default function ProjectHub() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  
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

  const updateMut = useMutation({
    mutationFn: (data: Partial<Project>) => updateProject(editingProject!.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] });
      setShowForm(false);
      setEditingProject(null);
      setName('');
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });

  const deleteAllMut = useMutation({
    mutationFn: () => deleteAllProjects(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });

  const handleEditClick = (e: React.MouseEvent, p: Project) => {
    e.stopPropagation();
    setEditingProject(p);
    setName(p.name);
    setStyle(p.style);
    setAspect(p.aspect_ratio);
    setShowForm(true);
  };

  const handleNewClick = () => {
    setEditingProject(null);
    setName('');
    setStyle('2d_anime');
    setAspect('9:16');
    setShowForm(true);
  };

  const handleSubmit = () => {
    if (editingProject) {
      updateMut.mutate({ name, style, aspect_ratio: aspect });
    } else {
      createMut.mutate();
    }
  };

  const handleDeleteAll = () => {
    const doubleConfirm = confirm(
      'WARNING: Are you absolutely sure you want to delete ALL projects? This will wipe out all scenes, shots, assets, and characters! This action is irreversible.'
    );
    if (doubleConfirm) {
      const typedConfirmation = prompt('Please type "DELETE ALL" to confirm bulk deletion:');
      if (typedConfirmation === 'DELETE ALL') {
        deleteAllMut.mutate();
      } else {
        alert('Confirmation text mismatch. Deletion cancelled.');
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-500/30 border-t-accent-500 rounded-full animate-spin" />
          <p className="text-sm text-gray-500">Loading projects...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Studio Projects</h1>
          <p className="text-sm text-gray-500 mt-1">
            {projects?.length || 0} project{(projects?.length || 0) !== 1 ? 's' : ''} in your studio
          </p>
        </div>
        <div className="flex gap-2.5">
          {projects && projects.length > 0 && (
            <button
              onClick={handleDeleteAll}
              disabled={deleteAllMut.isPending}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/25 hover:bg-red-500 hover:text-white transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              {deleteAllMut.isPending ? 'Clearing...' : 'Clear All'}
            </button>
          )}
          <button onClick={handleNewClick} className="btn-primary flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Project
          </button>
        </div>
      </div>

      {/* Form (Create / Edit) */}
      {showForm && (
        <div className="card-glow mb-8 animate-slide-up">
          <div className="card p-5">
            <h2 className="text-sm font-semibold text-white mb-4">
              {editingProject ? `Edit Project: ${editingProject.name}` : 'Create New Project'}
            </h2>
            <div className="space-y-4">
              <input
                placeholder="Project name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-field"
                autoFocus
              />
              <div className="flex flex-col md:flex-row gap-3">
                <div className="flex-1">
                  <label className="text-xs text-gray-500 block mb-1.5 font-medium">Animation Style</label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {STYLES.map((s) => (
                      <button
                        key={s.value}
                        onClick={() => setStyle(s.value)}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                          style === s.value
                            ? 'bg-accent-500/20 border border-accent-500/30 text-accent-300'
                            : 'bg-surface-700 border border-transparent text-gray-400 hover:text-white'
                        }`}
                      >
                        <span>{s.icon}</span>
                        <span>{s.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
                <div className="w-full md:w-32">
                  <label className="text-xs text-gray-500 block mb-1.5 font-medium">Aspect Ratio</label>
                  <select
                    value={aspect}
                    onChange={(e) => setAspect(e.target.value)}
                    className="input-field py-2"
                  >
                    {RATIOS.map((r) => (
                      <option key={r}>{r}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  onClick={handleSubmit}
                  disabled={!name.trim() || createMut.isPending || updateMut.isPending}
                  className="btn-primary"
                >
                  {createMut.isPending || updateMut.isPending ? (
                    <span className="flex items-center gap-2">
                      <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Saving...
                    </span>
                  ) : editingProject ? (
                    'Save Changes'
                  ) : (
                    'Create Project'
                  )}
                </button>
                <button
                  onClick={() => {
                    setShowForm(false);
                    setEditingProject(null);
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Project grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {projects?.map((p: Project, idx: number) => {
          const grad = STYLE_COLORS[p.style] || 'from-indigo-500 to-purple-600';
          return (
            <div
              key={p.id}
              className="card group cursor-pointer overflow-hidden animate-slide-up flex flex-col justify-between"
              style={{ animationDelay: `${idx * 60}ms` }}
              onClick={() => navigate(`/projects/${p.id}/story`)}
            >
              <div>
                {/* Color accent bar */}
                <div className={`h-1.5 bg-gradient-to-r ${grad}`} />

                <div className="p-5">
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <h3 className="font-semibold text-white text-lg truncate group-hover:text-accent-300 transition-colors">
                        {p.name}
                      </h3>
                      <div className="flex gap-2 mt-2">
                        <span className="badge bg-surface-700 text-gray-400 border border-accent-500/10">
                          {STYLES.find((s) => s.value === p.style)?.label || p.style}
                        </span>
                        <span className="badge bg-surface-700 text-gray-400 border border-accent-500/10">
                          {p.aspect_ratio}
                        </span>
                      </div>
                    </div>

                    {/* Quick actions (Edit / Delete) */}
                    <div className="flex items-center gap-1 ml-2 opacity-50 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => handleEditClick(e, p)}
                        className="text-gray-500 hover:text-accent-300 p-1 rounded hover:bg-accent-500/10 transition-colors"
                        title="Edit Project"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Delete "${p.name}"? This cannot be undone.`)) deleteMut.mutate(p.id);
                        }}
                        className="text-gray-500 hover:text-red-400 p-1 rounded hover:bg-red-500/10 transition-colors"
                        title="Delete Project"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="px-5 pb-5">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {new Date(p.created_at).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {(!projects || projects.length === 0) && !showForm && (
        <div className="text-center py-20">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-accent-500/20 to-purple-500/20 border border-accent-500/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </div>
          <p className="text-gray-400 font-medium">No projects yet</p>
          <p className="text-sm text-gray-600 mt-1">Create your first project to get started</p>
          <button onClick={handleNewClick} className="btn-primary mt-4">
            Create Project
          </button>
        </div>
      )}
    </div>
  );
}
