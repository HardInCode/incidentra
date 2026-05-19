import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import en from '../i18n/locales/en.json';
import id from '../i18n/locales/id.json';

export const LANG_STORAGE_KEY = 'sme-guard-lang';

const LOCALES = { en, id };

const LanguageContext = createContext(null);

function getNested(obj, path) {
  return path.split('.').reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), obj);
}

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    try {
      const stored = localStorage.getItem(LANG_STORAGE_KEY);
      return stored === 'id' ? 'id' : 'en';
    } catch {
      return 'en';
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(LANG_STORAGE_KEY, language);
    } catch {
      /* ignore */
    }
    document.documentElement.setAttribute('lang', language);
  }, [language]);

  const value = useMemo(() => {
    const t = (key, vars) => {
      let str = getNested(LOCALES[language], key) ?? getNested(LOCALES.en, key) ?? key;
      if (vars && typeof str === 'string') {
        Object.entries(vars).forEach(([k, v]) => {
          str = str.replace(new RegExp(`{{${k}}}`, 'g'), String(v));
        });
      }
      return str;
    };
    return { language, setLanguage, t };
  }, [language]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}
