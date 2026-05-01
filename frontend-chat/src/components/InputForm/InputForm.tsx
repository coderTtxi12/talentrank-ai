'use client';

import React, { useEffect, useRef } from 'react';
import { InputFormProps } from '@/types';
import styles from './InputForm.module.css';

export const InputForm: React.FC<InputFormProps> = ({
  inputValue,
  setInputValue,
  onSubmit,
  isLoading,
  inputRef,
  fileInputRef,
  onFileSelect,
  onOpenFileDialog,
  selectedFiles = [],
  placeholder = "Ask anything",
  className = ""
}) => {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const scrollHeight = textarea.scrollHeight;
      const maxHeight = 120;
      const minHeight = 24;
      
      if (scrollHeight > maxHeight) {
        textarea.style.height = `${maxHeight}px`;
        textarea.style.overflowY = 'auto';
      } else if (scrollHeight < minHeight) {
        textarea.style.height = `${minHeight}px`;
        textarea.style.overflowY = 'hidden';
      } else {
        textarea.style.height = `${scrollHeight}px`;
        textarea.style.overflowY = 'hidden';
      }
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [inputValue]);

  useEffect(() => {
    adjustTextareaHeight();
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    adjustTextareaHeight();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (inputValue.trim() && !isLoading) {
        onSubmit(e as unknown as React.FormEvent);
      }
    }
  };

  return (
    <form onSubmit={onSubmit} className={`${styles.inputForm} ${className}`}>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={onFileSelect}
        style={{ display: 'none' }}
        accept="*/*"
      />
      <div className={styles.inputContainer}>
        <textarea
          ref={(el) => {
            if (inputRef) inputRef.current = el;
            textareaRef.current = el;
          }}
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={styles.messageInput}
          disabled={isLoading}
          rows={1}
        />
        <button
          type="submit"
          className={`${styles.sendButton} ${selectedFiles.length > 0 ? styles.hasFiles : ''}`}
          disabled={isLoading || (!inputValue.trim() && selectedFiles.length === 0)}
        >
          <span className="material-icons">send</span>
        </button>
      </div>
    </form>
  );
};

