'use client';

import React from 'react';
import { WelcomeSectionProps } from '@/types';
import { InputForm } from '../InputForm/InputForm';
import { FilePreview } from '../FilePreview/FilePreview';
import styles from './WelcomeSection.module.css';

export const WelcomeSection: React.FC<WelcomeSectionProps> = ({ 
  inputValue, 
  setInputValue, 
  onSubmit, 
  isLoading, 
  inputRef,
  fileInputRef,
  onFileSelect,
  onOpenFileDialog,
  selectedFiles,
  onRemoveFile
}) => {
  return (
    <div className={styles.welcomeSection}>
      <h2 className={styles.welcomeTitle}>Chat with your restaurant data</h2>
      <p className={styles.welcomeDescription}>
        Query sales, revenue, and performance metrics using natural language
      </p>
      <FilePreview 
        files={selectedFiles}
        onRemoveFile={onRemoveFile}
      />
      <InputForm
        inputValue={inputValue}
        setInputValue={setInputValue}
        onSubmit={onSubmit}
        isLoading={isLoading}
        inputRef={inputRef}
        fileInputRef={fileInputRef}
        onFileSelect={onFileSelect}
        onOpenFileDialog={onOpenFileDialog}
        selectedFiles={selectedFiles}
        placeholder="Ask anything"
        className="centered-input-form"
      />
    </div>
  );
};

