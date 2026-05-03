'use client';

import React from 'react';
import {
  CHAT_BTN_NEW_CONVERSATION,
  CHAT_HEADER_TITLE,
  CHAT_THEME_TITLE_TO_DARK,
  CHAT_THEME_TITLE_TO_LIGHT,
} from '@/constants/branding';
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
          {CHAT_HEADER_TITLE}
        </h1>
      </div>
      <div className={styles.headerRight}>
        <button 
          className={styles.themeToggle} 
          onClick={toggleTheme} 
          title={theme === 'dark' ? CHAT_THEME_TITLE_TO_LIGHT : CHAT_THEME_TITLE_TO_DARK}
        >
          <span className="material-icons">
            {theme === 'dark' ? 'light_mode' : 'dark_mode'}
          </span>
        </button>
        <button 
          className={styles.headerButton} 
          onClick={onClearChat} 
          title={CHAT_BTN_NEW_CONVERSATION}
        >
          <span className="material-icons">refresh</span>
        </button>
      </div>
    </header>
  );
};

