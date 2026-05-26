import { Link, useParams } from 'react-router-dom';
import { useUiStore } from '../store/uiStore';
import { useQuery } from '@tanstack/react-query';
import { getProject } from '../api/endpoints';

const navItems = [
  { label: 'Story', path: 'story', icon: '📖' },
  { label: 'Characters', path: 'characters', icon: '👤' },
  { label: 'Timeline', path: 'timeline', icon: '🎬' },
  { label: 'Export', path: 'export', icon: '📦' },
];

export default function Sidebar() {
  const { id } = useParams<{ id: string }>();
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const { data: project } = useQuery({
    queryKey: ['project', id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  });

  if (!sidebarOpen) {
    return (
      <button
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-50 p-2 bg-gray-800 text-white rounded"
      >
        ☰
      </button>
    );
  }

  return (
    <aside className="w-64 h-screen bg-gray-900 text-white flex flex-col shrink-0">
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <Link to="/" className="font-bold text-lg">
            🎬 Pipeline
          </Link>
          <button onClick={toggleSidebar} className="text-gray-400 hover:text-white">
            ✕
          </button>
        </div>
        {project && (
          <p className="text-sm text-gray-400 mt-1 truncate">{project.name}</p>
        )}
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {id &&
          navItems.map((item) => (
            <Link
              key={item.path}
              to={`/projects/${id}/${item.path}`}
              className="flex items-center gap-3 px-3 py-2 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition-colors"
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        <Link
          to="/"
          className="flex items-center gap-3 px-3 py-2 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition-colors mt-4"
        >
          <span>←</span>
          <span>All Projects</span>
        </Link>
      </nav>
    </aside>
  );
}
