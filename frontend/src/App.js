import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { ThemeProvider, useThemeMode } from './context/ThemeContext';
import { LanguageProvider } from './context/LanguageContext';
import Layout from './components/shared/Layout';
import Dashboard from './pages/Dashboard';
import Incidents from './pages/Incidents';
import LiveTraffic from './pages/LiveTraffic';
import IncidentDetail from './pages/IncidentDetail';
import BlockedIPs from './pages/BlockedIPs';
import DetectionRules from './pages/DetectionRules';
import Settings from './pages/Settings';
import AuditLog from './pages/AuditLog';
import Login from './pages/Login';
import ChatbotWidget from './components/shared/ChatbotWidget';
import SessionTimeoutWarning from './components/shared/SessionTimeoutWarning';

function AppRoutes({ isAuthenticated, onLogin, onLogout }) {
  const { mode } = useThemeMode();

  return (
    <>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/login" element={
            isAuthenticated ? <Navigate to="/" /> : <Login onLogin={onLogin} />
          } />
          <Route path="/*" element={
            isAuthenticated
              ? (
                <>
                  <Layout onLogout={onLogout}>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/incidents/all" element={<Incidents mode="all" />} />
                      <Route path="/incidents" element={<Incidents mode="ongoing" />} />
                      <Route path="/incidents/:id" element={<IncidentDetail />} />
                      <Route path="/blocked-ips" element={<BlockedIPs />} />
                      <Route path="/rules" element={<DetectionRules />} />
                      <Route path="/traffic" element={<LiveTraffic />} />
                      <Route path="/settings" element={<Settings />} />
                      <Route path="/audit" element={<AuditLog />} />
                    </Routes>
                    <ChatbotWidget />
                  </Layout>
                  <SessionTimeoutWarning onLogout={onLogout} />
                </>
              )
              : <Navigate to="/login" />
          } />
        </Routes>
      </Router>
      <ToastContainer position="bottom-right" theme={mode === 'dark' ? 'dark' : 'light'} autoClose={4000} />
    </>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('sme_token');
    if (token) setIsAuthenticated(true);
  }, []);

  const handleLogin = (token) => {
    localStorage.setItem('sme_token', token);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('sme_token');
    setIsAuthenticated(false);
  };

  return (
    <LanguageProvider>
      <ThemeProvider>
        <AppRoutes
          isAuthenticated={isAuthenticated}
          onLogin={handleLogin}
          onLogout={handleLogout}
        />
      </ThemeProvider>
    </LanguageProvider>
  );
}

export default App;
