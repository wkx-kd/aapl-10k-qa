import { useState } from 'react';
import type { TabType } from './types';
import Layout from './components/common/Layout';
import FilterSidebar from './components/sidebar/FilterSidebar';
import ChatPanel from './components/chat/ChatPanel';
import FinancialDashboard from './components/dashboard/FinancialDashboard';
import GraphViewer from './components/graph/GraphViewer';
import { useChat } from './hooks/useChat';
import { useFilters } from './hooks/useFilters';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const { messages, isStreaming, sendMessage, clearMessages } = useChat();
  const {
    filters,
    availableYears,
    availableSections,
    toggleYear,
    toggleSection,
    clearFilters,
  } = useFilters();

  return (
    <Layout
      activeTab={activeTab}
      onTabChange={setActiveTab}
      sidebar={
        <FilterSidebar
          filters={filters}
          availableYears={availableYears}
          availableSections={availableSections}
          onToggleYear={toggleYear}
          onToggleSection={toggleSection}
          onClear={clearFilters}
        />
      }
    >
      {activeTab === 'chat' && (
        <ChatPanel
          messages={messages}
          isStreaming={isStreaming}
          filters={filters}
          onSendMessage={sendMessage}
          onClear={clearMessages}
        />
      )}
      {activeTab === 'dashboard' && <FinancialDashboard />}
      {activeTab === 'graph' && <GraphViewer />}
    </Layout>
  );
}
