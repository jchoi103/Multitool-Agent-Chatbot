import React from 'react';
import styles from './Footer.module.css';

interface FooterProps {
  customText?: string;
}

const Footer: React.FC<FooterProps> = ({ customText }) => {
  const currentYear = new Date().getFullYear();
  const footerText = customText || `${currentYear} Demo Swish Store.`;
  
  return (
    <footer className={styles.footer}>
      <p>{footerText}</p>
    </footer>
  );
};

export default Footer;