'use client';

import { useState, useRef, useEffect } from 'react';
import { ChatRequestBody, Message, UseChatReturn } from '@/types';

// Generate or retrieve session ID from localStorage
// IMPORTANT: Generate a NEW session_id on each page load
const getSessionId = (): string => {
  if (typeof window === 'undefined') return '';
  
  try {
    // Always generate a new session ID (don't retrieve from localStorage)
    // This ensures a fresh session on each page reload
    const newSessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
    
    // Store it in localStorage for the current session (but won't be reused on reload)
    localStorage.setItem('orbio_chat_session_id', newSessionId);
    
    return newSessionId;
  } catch (error) {
    // Fallback if localStorage is not available
    console.warn('localStorage not available, using temporary session ID');
    return `session-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
  }
};

// API URL from environment (safe for SSR)
const getApiUrl = (): string => {
  if (typeof window !== 'undefined') {
    // Client-side: can use environment variable
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
  // Server-side: default
  return 'http://localhost:8000';
};

export const useChat = (): UseChatReturn => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [sessionId, setSessionId] = useState<string>('');

  // Initialize session ID on client side only
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setSessionId(getSessionId());
    }
  }, []);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!inputValue.trim() && selectedFiles.length === 0) || isLoading || isStreaming || !sessionId) return;

    const userInput = inputValue;
    const attachedFiles = [...selectedFiles];
    
    const userMessage: Message = {
      id: Date.now(),
      text: userInput,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString(),
      files: attachedFiles
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setSelectedFiles([]);
    setIsLoading(true);

    // Create AI message placeholder
    const aiMessage: Message = {
      id: Date.now() + 1,
      text: '',
      sender: 'ai',
      timestamp: new Date().toLocaleTimeString(),
      isStreaming: true
    };

    setMessages(prev => [...prev, aiMessage]);
    setIsStreaming(true);

    try {
      const apiUrl = getApiUrl();
      const sid = sessionId || getSessionId();
      const textPart = userInput.trim();
      const fileNote =
        attachedFiles.length > 0
          ? `[Adjuntos: ${attachedFiles.map((f) => f.name).join(', ')}]`
          : '';
      const message = [textPart, fileNote].filter(Boolean).join('\n\n');

      const body: ChatRequestBody = {
        session_id: sid,
        message,
      };

      const response = await fetch(`${apiUrl}/api/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        let detail = `${response.status} ${response.statusText}`;
        try {
          const errBody = await response.json();
          if (typeof errBody?.detail === 'string') {
            detail = errBody.detail;
          }
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }

      const data = await response.json();

      let answer =
        typeof data.reply === 'string' ? data.reply : 'No response received';
      
      // Update AI message with response
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage?.sender === 'ai' && lastMessage.isStreaming) {
          lastMessage.text = answer;
          lastMessage.imageBase64 = data.image_base64 || undefined;
          lastMessage.imageMime = data.image_mime || undefined;
          lastMessage.isStreaming = false;
        }
        return newMessages;
      });
      
    } catch (error) {
      console.error('Error calling API:', error);
      
      // Show error message
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage?.sender === 'ai' && lastMessage.isStreaming) {
          const apiUrl = getApiUrl();
          lastMessage.text = `**Error:** ${error instanceof Error ? error.message : 'Failed to get response from server'}\n\nPlease check that the backend is running at ${apiUrl}`;
          lastMessage.isStreaming = false;
        }
        return newMessages;
      });
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSelectedFiles([]);
    // Note: session_id persists in localStorage
    // It only changes when the page is reloaded
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(prev => [...prev, ...files]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  return {
    messages,
    inputValue,
    setInputValue,
    isLoading,
    isStreaming,
    selectedFiles,
    messagesEndRef,
    inputRef,
    fileInputRef,
    handleSubmit,
    handleFileSelect,
    removeFile,
    openFileDialog,
    clearChat
  };
};

