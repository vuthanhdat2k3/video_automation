import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import ProjectList from './pages/ProjectList';
import StoryEditor from './pages/StoryEditor';
import CharacterList from './pages/CharacterList';
import CharacterEditor from './pages/CharacterEditor';
import Timeline from './pages/Timeline';
import ShotEditor from './pages/ShotEditor';
import ExportPanel from './pages/ExportPanel';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 10000,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<ProjectList />} />
            <Route path="/projects/:id/story" element={<StoryEditor />} />
            <Route path="/projects/:id/characters" element={<CharacterList />} />
            <Route path="/projects/:id/characters/:cid" element={<CharacterEditor />} />
            <Route path="/projects/:id/timeline" element={<Timeline />} />
            <Route path="/projects/:id/scenes/:sid" element={<ShotEditor />} />
            <Route path="/projects/:id/export" element={<ExportPanel />} />
            <Route path="*" element={
              <div className="text-center py-12 text-gray-500">
                <h2 className="text-xl font-bold mb-2">404</h2>
                <p>Page not found</p>
              </div>
            } />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
