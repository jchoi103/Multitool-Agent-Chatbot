import React, { useState, useEffect } from 'react';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { useLocation, useNavigate } from 'react-router-dom';
import NavigationBar from '../components/navigation/NavigationBar';
import Footer from '../components/footer/Footer';
import styles from './pages.module.css';
import pageSpecificStyles from './AuthPage.module.css';
import { getSupabaseClient } from '../utils/supabaseClient';
import { Toaster, toast } from 'react-hot-toast';

const AuthPage: React.FC = () => {
  const [supabase, setSupabase] = useState<SupabaseClient | null>(null);
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const location = useLocation();
  const navigate = useNavigate();
  const redirectPath = new URLSearchParams(location.search).get('redirect') || '/products';

  useEffect(() => {
    async function setup() {
      try {
        const client = await getSupabaseClient();
        setSupabase(client);

        const { data } = await client.auth.getSession();
        if (data.session) navigate(redirectPath);
      } catch (err) {
        setError('Failed to initialize authentication system.');
      }
    }
    setup();
  }, [redirectPath, navigate]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    if (!supabase) {
      setError('Supabase not initialized.');
      setIsLoading(false);
      return;
    }

    try {
      let response;

      if (isLogin) {
        response = await supabase.auth.signInWithPassword({ email, password });
      } else {
        if (password !== confirmPassword) {
          setError('Passwords do not match.');
          setIsLoading(false);
          return;
        }
        response = await supabase.auth.signUp({ email, password });
      }

      if (response.error) {
        setError(response.error.message);
      } else {
        const token = response.data.session?.access_token;
        if (token) {
          localStorage.setItem('authToken', token);
          localStorage.setItem('userEmail', email);
          toast.success(`${isLogin ? 'Login' : 'Signup'} successful! Redirecting...`);
          setTimeout(() => navigate(redirectPath), 1500);
        } else {
          setError('Check your email to confirm your account if signing up.');
        }
      }
    } catch (err) {
      console.error(err);
      setError('An unexpected error occurred.');
    }
    setIsLoading(false);
  };

  if (!supabase) {
    return (
      <div className={styles.pageContainer}>
        <NavigationBar />
        <main className={`${styles.pageContent} ${pageSpecificStyles.authContent}`}>
          <p>Loading authentication system...</p>
        </main>
        <Footer customText="Example Swish Store. Auth." />
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      <Toaster position="top-center" reverseOrder={false} />
      <NavigationBar />
      <main className={`${styles.pageContent} ${pageSpecificStyles.authContent}`}>
        <div className={pageSpecificStyles.authFormContainer}>
          <h2>{isLogin ? 'Login' : 'Sign Up'}</h2>
          <form onSubmit={handleSubmit}>
            <div className={pageSpecificStyles.formGroup}>
              <label htmlFor="email">Email:</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className={pageSpecificStyles.formGroup}>
              <label htmlFor="password">Password:</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {!isLogin && (
              <div className={pageSpecificStyles.formGroup}>
                <label htmlFor="confirmPassword">Confirm Password:</label>
                <input
                  type="password"
                  id="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>
            )}
            {error && <p className={pageSpecificStyles.errorMessage}>{error}</p>}
            <button type="submit" disabled={isLoading} className={pageSpecificStyles.submitButton}>
              {isLoading ? 'Processing...' : isLogin ? 'Login' : 'Sign Up'}
            </button>
          </form>
          <button
            onClick={() => {
              setIsLogin(!isLogin);
              setError(null);
            }}
            className={pageSpecificStyles.toggleFormButton}
          >
            {isLogin ? 'Need an account? Sign Up' : 'Already have an account? Login'}
          </button>
          {isLogin && (
            <a
              href="#"
              className={pageSpecificStyles.forgotPasswordLink}
              onClick={(e) => {
                e.preventDefault();
                toast('Forgot password functionality not implemented yet.');
              }}
            >
              Forgot Password?
            </a>
          )}
        </div>
      </main>
      <Footer customText="Example Swish Store. Auth." />
    </div>
  );
};

export default AuthPage;
