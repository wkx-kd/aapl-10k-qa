import type { ReactNode } from 'react';
import type { TabType } from '../../types';
import { MessageSquare, BarChart3, Share2 } from 'lucide-react';

interface LayoutProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  sidebar: ReactNode;
  children: ReactNode;
}

const tabs: { key: TabType; label: string; icon: ReactNode }[] = [
  { key: 'chat', label: 'Chat', icon: <MessageSquare size={18} /> },
  { key: 'dashboard', label: 'Dashboard', icon: <BarChart3 size={18} /> },
  { key: 'graph', label: 'Graph', icon: <Share2 size={18} /> },
];

export default function Layout({ activeTab, onTabChange, sidebar, children }: LayoutProps) {
  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">A</span>
          </div>
          <h1 className="text-lg font-semibold text-slate-800">AAPL 10-K Intelligence</h1>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">2020-2025</span>
        </div>

        {/* Tab Navigation */}
        <nav className="flex gap-1 bg-slate-100 rounded-lg p-1">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => onTabChange(tab.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                activeTab === tab.key
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-56 bg-white border-r border-slate-200 p-4 overflow-y-auto shrink-0">
          {sidebar}
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
