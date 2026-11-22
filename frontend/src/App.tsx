import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { GuestRoute, ProtectedRoute } from './auth/ProtectedRoute';
import { AccountPage } from './pages/AccountPage';
import { DashboardPage } from './pages/DashboardPage';
import { JournalEditorPage } from './pages/JournalEditorPage';
import { JournalEntryPage } from './pages/JournalEntryPage';
import { JournalPage } from './pages/JournalPage';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { TagsPage } from './pages/TagsPage';
import './App.css';

export const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/login"
        element={
          <GuestRoute>
            <LoginPage />
          </GuestRoute>
        }
      />
      <Route
        path="/signup"
        element={
          <GuestRoute>
            <SignupPage />
          </GuestRoute>
        }
      />
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route path="/tags" element={<TagsPage />} />
        <Route path="/journal" element={<JournalPage />} />
        <Route path="/journal/new" element={<JournalEditorPage />} />
        <Route path="/journal/:entryId" element={<JournalEntryPage />} />
        <Route path="/journal/:entryId/edit" element={<JournalEditorPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
