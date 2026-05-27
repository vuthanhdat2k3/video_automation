import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import ProjectHub from './pages/ProjectHub';
import StoryLab from './pages/StoryLab';
import CharacterGallery from './pages/CharacterGallery';
import CharacterProfile from './pages/CharacterProfile';
import PipelineTimeline from './pages/PipelineTimeline';
import ShotStudio from './pages/ShotStudio';
import ExportCenter from './pages/ExportCenter';

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
            <Route path="/" element={<ProjectHub />} />
            <Route path="/projects/:id/story" element={<StoryLab />} />
            <Route path="/projects/:id/characters" element={<CharacterGallery />} />
            <Route path="/projects/:id/characters/:cid" element={<CharacterProfile />} />
            <Route path="/projects/:id/timeline" element={<PipelineTimeline />} />
            <Route path="/projects/:id/scenes/:sid" element={<ShotStudio />} />
            <Route path="/projects/:id/export" element={<ExportCenter />} />
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
