'use client';

import React from 'react';
import styles from './TypingIndicator.module.css';

export const TypingIndicator: React.FC = () => {
  return (
    <div className={`${styles.message} ${styles.ai}`}>
      <div className={styles.messageContent}>
        <div className={styles.planningText}>Planning</div>
        <div className={styles.typingIndicator}>
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
};

