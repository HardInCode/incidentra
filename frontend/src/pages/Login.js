/**
 * LOGIN & SELF-REGISTRATION PAGE — calls POST /api/auth/login and /api/auth/register.
 * Ctrl+F: handleLogin, handleRegister, mode (login/register toggle)
 * Backend counterpart: backend/app/api/auth.py
 */
import React, { useState } from 'react';                                                                              //import the necessary components from the React library
import { Box, Card, CardContent, Typography, TextField, Button, CircularProgress, Alert, Link } from '@mui/material'; //import the necessary components from the MUI library
import { login, register } from '../services/api';                                                                    //import the login and register functions from the api.js file
import { useLanguage } from '../context/LanguageContext';                                                             //import the useLanguage hook from the LanguageContext.js file

// Maps backend auth error codes (auth.py) → i18n keys — so alerts follow app language (en/id)
const AUTH_ERROR_I18N = {
  invalid_credentials: 'login.invalidCredentials',
  account_pending: 'login.accountPending',
  account_suspended: 'login.accountSuspended',
  account_inactive: 'login.accountInactive',
  register_rate_limited: 'login.registerRateLimited',
  register_fields_required: 'login.registerFieldsRequired',
  register_password_too_short: 'login.registerPasswordTooShortServer',
  username_exists: 'login.usernameExists',
  email_exists: 'login.emailExists',
};

function translateAuthError(err, t, fallbackKey) {
  const code = err.response?.data?.error;
  const i18nKey = code && AUTH_ERROR_I18N[code];
  if (i18nKey) return t(i18nKey);
  return t(fallbackKey);
}

//Login component def, it is used to login to the application
export default function Login({ onLogin }) {
  const { t } = useLanguage();                              //use the useLanguage hook to get the translation function
  const [mode, setMode] = useState('login');                // 'login' | 'register'
  const [loading, setLoading] = useState(false);            // loading state to show the loading spinner
  const [error, setError] = useState('');                   // error state to show the error message
  const [info, setInfo] = useState('');                     // info state to show the info message

  //login states to store the username and password
  const [username, setUsername] = useState(''); 
  const [password, setPassword] = useState(''); 

  //register states to store the register username, email, password and confirm password
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');

  //clearError function to clear the error message
  const clearError = () => {
    if (error) setError('');
  };

  //switchMode function to switch the mode between login and register
  const switchMode = (next) => {
    setMode(next);
    setError('');
    setInfo('');
  };
 
  // Login Function, send username and password to the backend
  const handleLogin = async (e) => {
    e.preventDefault();                 //e is the form submission event, prevent the default form submission behavior (page reload)
    setLoading(true);                   // set loading to true to show the loading spinner
    try {
      // send the username and password to the backend
      const res = await login(username, password);            // use the login function from the api.js file and wait for the response
      setError('');                                           // clear the error
      onLogin(res.data.token);                                // prop onLogin = App.js handleLogin(token) → localStorage + isAuthenticated (from App.js)
    } catch (err) {
      setError(translateAuthError(err, t, 'login.invalidCredentials'));
    } finally {
      setLoading(false);                                      // set loading to false to hide the loading spinner
    }
  };

  // Register — confirmPassword validated here only; backend receives username, email, password
  const handleRegister = async (e) => {
    e.preventDefault();                       //e is the form submission event, prevent the default form submission behavior (page reload)
    setError('');                             // clear the error
    if (regPassword !== regConfirm) {         // check if the password and confirm password are the same
      setError(t('login.passwordMismatch'));  // set the error to the error message from the language context (frontend/src/context/LanguageContext.js)
      return;                                 // return to stop the function execution
    }
    if (regPassword.length < 8) {             // check if the password is less than 8 characters
      setError(t('login.passwordTooShort'));  // set the error to the error message from the language context (frontend/src/context/LanguageContext.js)
      return;                                 // return to stop the function execution
    }
    setLoading(true);                         // set loading to true to show the loading spinner
    try {
      await register({ username: regUsername, email: regEmail, password: regPassword }); // POST /api/auth/register — confirmPassword frontend-only
      setInfo(t('login.registerSuccess'));      // set the info to the success message from the language context (frontend/src/context/LanguageContext.js)
      setRegUsername('');                       // clear the register username
      setRegEmail('');                          // clear the register email
      setRegPassword('');                       // clear the register password
      setRegConfirm('');                        // clear the register confirm password
      setMode('login');                         // set the mode to login
    } catch (err) {
      setError(translateAuthError(err, t, 'login.registerFailed'));
    } finally {
      setLoading(false);                         // set loading to false to hide the loading spinner
    }
  };

  // return the login page component
  return (
    <Box sx={{
      minHeight: '100vh',                        // set the minimum height to 100vh
      display: 'flex',                           // display the box as a flex container
      alignItems: 'center',                      // align the items to the center
      justifyContent: 'center',                  // justify the content to the center
      bgcolor: 'background.default',             // set the background color to the default background color
    }}>
      <Card sx={{ width: '100%', maxWidth: 420, mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Box
              component="img"
              src="/icons/incidentra.png"
              alt={t('brand.full')}
              sx={{ width: 64, height: 64, borderRadius: 3, mb: 2, objectFit: 'contain' }}
            />
            <Typography variant="h5" sx={{ fontWeight: 800, color: 'primary.main' }}>{t('login.title')}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
              {t('login.subtitle')}
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
              {error}
            </Alert>
          )}
          {info && (
            <Alert severity="success" sx={{ mb: 2 }} onClose={() => setInfo('')}>
              {info}
            </Alert>
          )}

          {mode === 'login' ? (
            <>
              <form onSubmit={handleLogin}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    fullWidth label={t('login.username')}        // set the label to the username
                    value={username}                             // set the value to the username
                    onChange={e => { setUsername(e.target.value); clearError(); }}  // onChange is the change event, call the setUsername function and clear the error
                    autoComplete="username"                                         // autoComplete is the autocomplete attribute, set the autocomplete to username
                  />
                  <TextField
                    fullWidth label={t('login.password')}        
                    type="password"
                    value={password}
                    onChange={e => { setPassword(e.target.value); clearError(); }}
                    autoComplete="current-password"
                  />
                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    color="primary"
                    size="large"
                    disabled={loading || !username || !password}        // disable the button if the loading is true or the username or password is empty
                    sx={{ mt: 1, py: 1.5, fontWeight: 700 }}
                  >
                    {loading ? <CircularProgress size={24} color="inherit" /> : t('login.signIn')}
                  </Button>
                </Box>
              </form>

              <Box sx={{ mt: 3, p: 2, bgcolor: 'action.hover', borderRadius: 2 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
                  {t('login.noAccountHint')}
                </Typography>
              </Box>

              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  {t('login.noAccountPrompt')}{' '}
                  <Link component="button" type="button" onClick={() => switchMode('register')} sx={{ fontWeight: 700 }}>
                    {t('login.registerLink')}
                  </Link>
                </Typography>
              </Box>
            </>
          ) : (
            <>
              <form onSubmit={handleRegister}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    fullWidth label={t('login.username')}
                    value={regUsername}
                    onChange={e => { setRegUsername(e.target.value); clearError(); }}
                    autoComplete="username"
                  />
                  <TextField
                    fullWidth label={t('login.email')}
                    type="email"
                    value={regEmail}
                    onChange={e => { setRegEmail(e.target.value); clearError(); }}
                    autoComplete="email"
                  />
                  <TextField
                    fullWidth label={t('login.password')}
                    type="password"
                    value={regPassword}
                    onChange={e => { setRegPassword(e.target.value); clearError(); }}
                    autoComplete="new-password"
                    helperText={t('login.passwordHint')}
                  />
                  <TextField
                    fullWidth label={t('login.confirmPassword')}
                    type="password"
                    value={regConfirm}
                    onChange={e => { setRegConfirm(e.target.value); clearError(); }}
                    autoComplete="new-password"
                  />
                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    color="primary"
                    size="large"
                    disabled={loading || !regUsername || !regEmail || !regPassword || !regConfirm}
                    sx={{ mt: 1, py: 1.5, fontWeight: 700 }}
                  >
                    {loading ? <CircularProgress size={24} color="inherit" /> : t('login.registerButton')}
                  </Button>
                </Box>
              </form>

              <Box sx={{ mt: 3, p: 2, bgcolor: 'action.hover', borderRadius: 2 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
                  {t('login.registerHint')}
                </Typography>
              </Box>

              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  {t('login.haveAccountPrompt')}{' '}
                  <Link component="button" type="button" onClick={() => switchMode('login')} sx={{ fontWeight: 700 }}>
                    {t('login.signIn')}
                  </Link>
                </Typography>
              </Box>
            </>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
