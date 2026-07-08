import React, { createContext, useContext, useMemo, useState } from 'react';

const ChatbotContext = createContext(null);

export function ChatbotProvider({ children }) {
  const [incidentContext, setIncidentContext] = useState(null);
  const value = useMemo(
    () => ({ incidentContext, setIncidentContext }),
    [incidentContext],
  );
  return (
    <ChatbotContext.Provider value={value}>
      {children}
    </ChatbotContext.Provider>
  );
}

export function useChatbotContext() {
  const ctx = useContext(ChatbotContext);
  if (!ctx) {
    throw new Error('useChatbotContext must be used within ChatbotProvider');
  }
  return ctx;
}
