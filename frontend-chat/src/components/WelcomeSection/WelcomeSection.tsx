'use client';

import React from 'react';
import { CHAT_INPUT_PLACEHOLDER, CHAT_WELCOME_TITLE } from '@/constants/branding';
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
      <h2 className={styles.welcomeTitle}>{CHAT_WELCOME_TITLE}</h2>
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
        placeholder={CHAT_INPUT_PLACEHOLDER}
        className="centered-input-form"
      />
    </div>
  );
};

