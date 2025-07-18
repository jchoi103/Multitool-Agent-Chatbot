import React, { useState, useEffect, useRef } from 'react';
import styles from './navigation.module.css';
import logo from '/src/assets/react.svg';
import { getSupabaseClient } from '../../utils/supabaseClient';
import { toast } from 'react-hot-toast';
import { FaUserCircle, FaCaretDown } from 'react-icons/fa';

const NavigationBar: React.FC = () => {
  const [isAccountDropdownOpen, setIsAccountDropdownOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);

  // Initialize supabase and check for logged-in user email
  useEffect(() => {
    async function fetchUser() {
      try {
        const supabase = await getSupabaseClient();
        const { data } = await supabase.auth.getSession();
        if (data.session?.user?.email) {
          setUserEmail(data.session.user.email);
        } else {
          setUserEmail(null);
        }
      } catch (err) {
        console.error('Failed to get user session:', err);
      }
    }
    fetchUser();
  }, []);

  const toggleMobileMenu = () => setIsMobileMenuOpen(!isMobileMenuOpen);
  const toggleAccountDropdown = () =>
    setIsAccountDropdownOpen(!isAccountDropdownOpen);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        accountMenuRef.current &&
        !accountMenuRef.current.contains(event.target as Node)
      ) {
        setIsAccountDropdownOpen(false);
      }
      if (
        mobileMenuRef.current &&
        !mobileMenuRef.current.contains(event.target as Node) &&
        !(event.target as HTMLElement).closest(`.${styles.hamburgerButton}`)
      ) {
        setIsMobileMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleLogout = async () => {
    try {
      const supabase = await getSupabaseClient();
      await supabase.auth.signOut();
      localStorage.clear();
      toast.success('Logged out!');
      setUserEmail(null);
      setIsAccountDropdownOpen(false);
      window.location.href = '/auth';
    } catch (error) {
      console.error('Failed to logout properly:', error);
      toast.error('Logout failed.');
    }
  };

  return (
    <nav className={styles.navBar}>
      <div className={styles.navLeft}>
        <a href="/products" className={styles.logoLink}>
          <img src={logo} alt="Swish Store Logo" className={styles.logo} />
          <span className={styles.storeName}>Swish Store</span>
        </a>
      </div>

      <button className={styles.hamburgerButton} onClick={toggleMobileMenu}>
        <span className={styles.hamburgerIconBar}></span>
        <span className={styles.hamburgerIconBar}></span>
        <span className={styles.hamburgerIconBar}></span>
      </button>

      <div
        className={`${styles.desktopNavItems} ${
          isMobileMenuOpen ? styles.hideOnMobile : ''
        }`}
      >
        <div className={styles.navCenter}>
          <a href="/products" className={styles.navLink}>
            Products
          </a>
          <a href="/cart" className={styles.navLink}>
            Shopping Cart
          </a>
        </div>
        <div className={styles.navRight} ref={accountMenuRef}>
          <div className={styles.accountMenu}>
            {!userEmail ? (
              <a href="/auth" className={styles.navLink}>
                Login/Register
              </a>
            ) : (
              <>
                <button
                  onClick={toggleAccountDropdown}
                  className={`${styles.navLink} ${styles.accountButton}`}
                  aria-haspopup="true"
                  aria-expanded={isAccountDropdownOpen}
                >
                  <FaUserCircle style={{ marginRight: 6, verticalAlign: 'middle' }} />
                  {userEmail}
                  <FaCaretDown style={{ marginLeft: 6, verticalAlign: 'middle' }} />
                </button>
                {isAccountDropdownOpen && (
                  <div className={styles.dropdownMenu}>
                    <button onClick={handleLogout} className={styles.dropdownItem}>
                      Log Out
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      {isMobileMenuOpen && (
        <div className={styles.mobileNavMenu} ref={mobileMenuRef}>
          {userEmail && (
            <div
              className={styles.mobileUserSection}
              style={{ marginBottom: '10px', paddingLeft: '30px' }}
            >
              <FaUserCircle style={{ marginRight: 6, verticalAlign: 'middle' }} />
              {userEmail}
            </div>
          )}
          <a href="/products" className={styles.mobileNavLink}>
            Products
          </a>
          <a href="/cart" className={styles.mobileNavLink}>
            Shopping Cart
          </a>
          {!userEmail ? (
            <a href="/auth" className={styles.mobileNavLink}>
              Login/Register
            </a>
          ) : (
            <button onClick={handleLogout} className={styles.mobileNavLink}>
              Log Out
            </button>
          )}
        </div>
      )}
    </nav>
  );
};

export default NavigationBar;
