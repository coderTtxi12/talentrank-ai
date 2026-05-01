'use client';

import React from 'react';
import { HeaderProps } from '@/types';
import styles from './Header.module.css';

export const Header: React.FC<HeaderProps> = ({ theme, toggleTheme, onClearChat }) => {
  const handleTitleClick = () => {
    onClearChat();
  };

  return (
    <header className={styles.header}>
      <div className={styles.headerLeft}>
        <h1 className={styles.headerTitle} onClick={handleTitleClick}>
          Data Analyst Agent
        </h1>
      </div>
      <div className={styles.headerRight}>
        <button 
          className={styles.themeToggle} 
          onClick={toggleTheme} 
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          <span className="material-icons">
            {theme === 'dark' ? 'light_mode' : 'dark_mode'}
          </span>
        </button>
        <button 
          className={styles.headerButton} 
          onClick={onClearChat} 
          title="Clear chat"
        >
          <span className="material-icons">refresh</span>
        </button>
      </div>
    </header>
  );
};

