'use client';

import React from 'react';
import { CHAT_TYPING_LABEL } from '@/constants/branding';
import styles from './TypingIndicator.module.css';

export const TypingIndicator: React.FC = () => {
  return (
    <div className={`${styles.message} ${styles.ai}`}>
      <div className={styles.messageContent}>
        <div className={styles.planningText}>{CHAT_TYPING_LABEL}…</div>
        <div className={styles.typingIndicator}>
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
};
