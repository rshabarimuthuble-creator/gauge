import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import { OverviewPage } from './pages/OverviewPage';
import { DatasetsPage } from './pages/DatasetsPage';
import { AgentVersionsPage } from './pages/AgentVersionsPage';
import { EvaluationsPage } from './pages/EvaluationsPage';
import { ComparisonsPage } from './pages/ComparisonsPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="versions" element={<AgentVersionsPage />} />
          <Route path="evaluations" element={<EvaluationsPage />} />
          <Route path="comparisons" element={<ComparisonsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
