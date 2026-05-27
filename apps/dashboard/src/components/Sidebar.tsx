import { Link, useParams, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getProject } from '../api/endpoints';
import { PIPELINE_STEPS } from '../types';

export default function Sidebar() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  });

  const currentPath = location.pathname.split('/').pop() || '';

  const STYLE_GRADIENTS: Record<string, string> = {
    '2d_chinese_donghua': 'from-amber-500 to-red-500',
    '2d_anime': 'from-blue-400 to-violet-500',
    '2d_western': 'from-orange-400 to-yellow-500',
    '3d_pixar': 'from-cyan-400 to-blue-500',
    '3d_realistic': 'from-gray-300 to-gray-500',
  };

  const styleGrad = STYLE_GRADIENTS[project?.style || ''] || 'from-indigo-500 to-purple-500';

  return (
    <aside className="w-64 h-screen bg-deep-900 border-r border-accent-500/10 flex flex-col shrink-0">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-accent-500/10">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-indigo-500/20 group-hover:shadow-indigo-500/40 transition-shadow">
            A
          </div>
          <div>
            <h1 className="font-semibold text-sm text-white">AI Animation</h1>
            <p className="text-[10px] text-gray-500">Studio Pipeline</p>
          </div>
        </Link>
      </div>

      {/* Project name */}
      {project && (
        <div className="px-5 py-3 border-b border-accent-500/10">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full bg-gradient-to-br ${styleGrad}`} />
            <span className="text-sm font-medium text-white truncate">{project.name}</span>
          </div>
          <div className="flex gap-2 mt-2">
            <span className="badge text-[10px] bg-surface-700 text-gray-400 border border-accent-500/10">
              {project.style?.replace('_', ' ').replace('2d', '2D').replace('3d', '3D')}
            </span>
            <span className="badge text-[10px] bg-surface-700 text-gray-400 border border-accent-500/10">
              {project.aspect_ratio}
            </span>
          </div>
        </div>
      )}

      {/* Pipeline Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-600 px-3 mb-3">
          Pipeline
        </p>
        {id &&
          PIPELINE_STEPS.map((step) => {
            const isActive = currentPath === step.id || (step.id === 'shots' && currentPath === 'scenes');
            const isScenesActive = currentPath === 'scenes' && step.id === 'shots';
            return (
              <Link
                key={step.id}
                to={`/projects/${id}/${step.id}`}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group ${
                  isActive || isScenesActive
                    ? 'bg-accent-500/10 text-white border border-accent-500/15'
                    : 'text-gray-400 hover:text-white hover:bg-white/[0.04] border border-transparent'
                }`}
              >
                <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-base transition-all ${
                  isActive || isScenesActive
                    ? 'bg-gradient-to-br from-accent-500 to-purple-600 shadow-lg shadow-accent-500/20'
                    : 'bg-surface-700 group-hover:bg-surface-600'
                }`}>
                  {step.icon}
                </span>
                <div>
                  <span className="text-sm font-medium">{step.label}</span>
                  <p className="text-[10px] text-gray-500">
                    {step.id === 'story' && 'Story bible & episodes'}
                    {step.id === 'characters' && 'Character management'}
                    {step.id === 'timeline' && 'Scene & shot overview'}
                    {step.id === 'shots' && 'Per-shot generation'}
                    {step.id === 'export' && 'Render & download'}
                  </p>
                </div>
              </Link>
            );
          })}
      </nav>

      {/* Bottom actions */}
      <div className="px-3 py-3 border-t border-accent-500/10">
        <Link
          to="/"
          className="flex items-center gap-2 px-3 py-2.5 rounded-xl text-gray-500 hover:text-white hover:bg-white/[0.04] transition-all text-sm"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
          </svg>
          All Projects
        </Link>
      </div>
    </aside>
  );
}
