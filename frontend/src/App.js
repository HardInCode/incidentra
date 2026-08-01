/**
 * APP ROOT — auth state, React Router, Layout wrapper.
 * Ctrl+F: handleLogin, handleLogout, isAuthenticated, AppRoutes
 * Flow: index.js → App → Login (onLogin prop) or Layout + pages
 */
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
import Users from './pages/Users';
import Login from './pages/Login';
import ChatbotWidget from './components/shared/ChatbotWidget';
import SessionTimeoutWarning from './components/shared/SessionTimeoutWarning';
import { ChatbotProvider } from './context/ChatbotContext';

function AppRoutes({ isAuthenticated, onLogin, onLogout }) {
  const { mode } = useThemeMode();

  return (
    <>
      <CssBaseline />
      <Router>
        <Routes>
          {/* authenticated → redirect / ; else show Login — onLogin prop = handleLogin from App() */}
          <Route path="/login" element={
            isAuthenticated ? <Navigate to="/" /> : <Login onLogin={onLogin} />
          } />
          <Route path="/*" element={
            isAuthenticated
              ? (
                <>
                  {/* ChatbotProvider = shared incidentContext; ChatbotWidget = floating UI */}
                  <ChatbotProvider>
                    <Layout onLogout={onLogout}>
                      <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/incidents/all" element={<Incidents key="incidents-all" mode="all" />} />
                        <Route path="/incidents" element={<Incidents key="incidents-ongoing" mode="ongoing" />} />
                        <Route path="/incidents/:id" element={<IncidentDetail />} />
                        <Route path="/blocked-ips" element={<BlockedIPs />} />
                        <Route path="/rules" element={<DetectionRules />} />
                        <Route path="/traffic" element={<LiveTraffic />} />
                        <Route path="/settings" element={<Settings />} />
                        <Route path="/users" element={<Users />} />
                        <Route path="/audit" element={<AuditLog />} />
                      </Routes>
                      <ChatbotWidget />
                    </Layout>
                  </ChatbotProvider>
                  <SessionTimeoutWarning onLogout={onLogout} />
                </>
              )
              : <Navigate to="/login" />
          } />
        </Routes>
      </Router>
      {/* react-toastify popups (toast.success etc.) — not the NotificationBell */}
      <ToastContainer position="top-right" theme={mode === 'dark' ? 'dark' : 'light'} autoClose={3000} limit={3} />
    </>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('incidentra_token'); // restore session on refresh
    if (token) setIsAuthenticated(true);
  }, []);

  const handleLogin = (token) => {                    // called via onLogin prop from Login.js
    localStorage.setItem('incidentra_token', token);
    setIsAuthenticated(true);                         // triggers Navigate to "/" → Dashboard
  };

  const handleLogout = () => {                        // passed to Layout + SessionTimeoutWarning (not Login.js)
    localStorage.removeItem('incidentra_token');
    setIsAuthenticated(false);
  };

  return (
    <LanguageProvider>
      <ThemeProvider>
        <AppRoutes
          isAuthenticated={isAuthenticated}
          onLogin={handleLogin}   // prop name onLogin → actual function handleLogin
          onLogout={handleLogout}
        />
      </ThemeProvider>
    </LanguageProvider>
  );
}

export default App;
