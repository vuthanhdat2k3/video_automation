import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import PipelineStepper from './PipelineStepper';

export default function Layout() {
  return (
    <div className="flex h-screen bg-deep-950 overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0 overflow-auto">
        {/* Pipeline Stepper Bar */}
        <div className="sticky top-0 z-30 bg-deep-950/90 backdrop-blur-xl border-b border-accent-500/10 px-6 py-3">
          <div className="max-w-6xl">
            <PipelineStepper />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 animate-fade-in">
          <div className="max-w-6xl mx-auto">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
}
