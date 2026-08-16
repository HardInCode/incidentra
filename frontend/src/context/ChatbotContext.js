/**
 * CHATBOT INCIDENT CONTEXT — state React global antara IncidentDetail dan ChatbotWidget.
 * Ctrl+F: CHATBOT_FLOW, INCIDENT_CONTEXT_FLOW, incidentContext, setIncidentContext
 *
 * INCIDENT_CONTEXT_FLOW (chatbot TIDAK SELECT DB sendiri):
 *   ① IncidentDetail.js fetchIncident → GET /incidents/:id → incidents.py SELECT PostgreSQL
 *   ② setIncident( res.data ) → useEffect → setIncidentContext( incident )
 *   ③ ChatbotWidget.js baca incidentContext → JSON.stringify → POST /chatbot/message { context }
 *   ④ chatbot.py chat_message → full_message = "[Incident Context: ...]\n\nQuestion: ..."
 *   ⑤ _get_groq_reply(history) — Groq baca JSON di prefix, tanpa query ulang
 *
 * Provider: App.js membungkus Layout + ChatbotWidget (hanya saat authenticated).
 * Cleanup: keluar IncidentDetail → setIncidentContext(null) — chip context hilang di widget.
 *
 * Beda AI_EXPLAIN_FLOW: explain = backend query DB + prompt khusus ai_service.py;
 *                        chatbot context = data incident sudah di-fetch frontend, dikirim ulang sebagai string.
 */
import React, { createContext, useContext, useMemo, useState } from 'react';

const ChatbotContext = createContext(null);

export function ChatbotProvider({ children }) {
  // null = halaman bukan IncidentDetail / incident belum load
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
