'use client';

import React, { useState, useMemo, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { MessageProps } from '@/types';
import styles from './Message.module.css';
import 'highlight.js/styles/github-dark.css';

// Custom image renderer with download and zoom functionality for charts
const ChartImageRenderer = ({ src, alt }: { src?: string; alt?: string }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showActions, setShowActions] = useState(false);

  if (!src) return null;

  // Check if it's a base64 data URL (chart from backend)
  const isChart = src.startsWith('data:image');

  if (!isChart) {
    // Regular image (not a chart)
    return <img src={src} alt={alt} style={{ maxWidth: '100%', borderRadius: '0.5rem' }} />;
  }

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    
    // Create a temporary link to download the image
    const link = document.createElement('a');
    link.href = src;
    link.download = alt || 'chart.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleZoom = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  return (
    <>
      <div 
        style={{ position: 'relative', display: 'inline-block', margin: '1rem 0', maxWidth: '100%' }}
        onMouseEnter={() => setShowActions(true)}
        onMouseLeave={() => setShowActions(false)}
      >
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <img 
            src={src} 
            alt={alt || 'Chart'} 
            style={{ 
              maxWidth: '100%', 
              height: 'auto', 
              borderRadius: '0.5rem',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
              cursor: 'pointer',
              transition: 'transform 0.2s'
            }}
            onClick={handleZoom}
          />
          <div style={{ 
            position: 'absolute', 
            top: '0.5rem', 
            right: '0.5rem', 
            display: 'flex', 
            gap: '0.5rem',
            opacity: showActions ? 1 : 0,
            transition: 'opacity 0.2s',
            pointerEvents: showActions ? 'auto' : 'none'
          }}>
            <button
              onClick={handleDownload}
              style={{
                background: 'rgba(0, 0, 0, 0.7)',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                padding: '0.5rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'background 0.2s'
              }}
              title="Download image"
              aria-label="Download image"
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.9)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.7)'}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </button>
            <button
              onClick={handleZoom}
              style={{
                background: 'rgba(0, 0, 0, 0.7)',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                padding: '0.5rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'background 0.2s'
              }}
              title="View larger"
              aria-label="View larger"
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.9)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(0, 0, 0, 0.7)'}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {isModalOpen && (
        <div 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.9)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            cursor: 'zoom-out'
          }}
          onClick={handleCloseModal}
        >
          <img 
            src={src} 
            alt={alt || 'Chart'} 
            style={{
              maxWidth: '90vw',
              maxHeight: '90vh',
              objectFit: 'contain',
              borderRadius: '0.5rem'
            }}
            onClick={(e) => e.stopPropagation()}
          />
          <button 
            style={{
              position: 'absolute',
              top: '1rem',
              right: '1rem',
              background: 'rgba(255, 255, 255, 0.2)',
              color: 'white',
              border: 'none',
              borderRadius: '50%',
              width: '3rem',
              height: '3rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.5rem',
              transition: 'background 0.2s'
            }}
            onClick={handleCloseModal}
            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.3)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)'}
            aria-label="Close"
          >
            ×
          </button>
        </div>
      )}
    </>
  );
};

export const Message: React.FC<MessageProps> = ({ message }) => {
  const { text, sender, timestamp, isStreaming, files = [], imageBase64, imageMime } = message;
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [showTimestamp, setShowTimestamp] = useState(false);
  const messageRef = useRef<HTMLDivElement>(null);

  // Build image data URL if imageBase64 is provided
  const imageDataUrl = imageBase64 && imageMime 
    ? `data:${imageMime};base64,${imageBase64}` 
    : null;

  // Show timestamp only after message is fully rendered and not streaming
  useEffect(() => {
    if (!isStreaming && messageRef.current) {
      // Small delay to ensure content is fully rendered
      const timer = setTimeout(() => {
        setShowTimestamp(true);
      }, 300);
      return () => clearTimeout(timer);
    } else if (isStreaming) {
      setShowTimestamp(false);
    }
  }, [isStreaming, text, imageDataUrl]);

  // Custom components for ReactMarkdown
  const markdownComponents = useMemo(() => ({
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <pre className={styles.codeBlock}>
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      ) : (
        <code className={styles.inlineCode} {...props}>
          {children}
        </code>
      );
    },
    pre({ children }: any) {
      return <div className={styles.codeWrapper}>{children}</div>;
    },
    img: (props: any) => {
      const { src, alt } = props;
      // Convert src to string if it's a Blob
      const srcString = typeof src === 'string' ? src : src?.toString() || '';
      return <ChartImageRenderer src={srcString} alt={alt} />;
    },
  }), []);

  return (
    <div className={`${styles.message} ${sender === 'user' ? styles.userMessage : styles.aiMessage}`}>
      {files.length > 0 && (
        <div className={styles.messageFilesContainer}>
          <div className={styles.messageFiles}>
            {files.map((file, index) => (
              <div key={index} className={styles.messageFile}>
                <div className={styles.filePreview}>
                  {file.type?.startsWith('image/') ? (
                    <img 
                      src={URL.createObjectURL(file)} 
                      alt={file.name}
                      onClick={() => setSelectedImage(URL.createObjectURL(file))}
                      style={{ cursor: 'pointer' }}
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                        if (target.nextSibling) {
                          (target.nextSibling as HTMLElement).style.display = 'flex';
                        }
                      }}
                    />
                  ) : null}
                  <div 
                    className={styles.fileIcon} 
                    style={{ display: file.type?.startsWith('image/') ? 'none' : 'flex' }}
                  >
                    <span className="material-icons">
                      {file.type?.startsWith('image/') ? 'image' : 'description'}
                    </span>
                  </div>
                </div>
                <div className={styles.fileInfo}>
                  <span className={styles.fileName}>{file.name}</span>
                  <span className={styles.fileSize}>
                    {(file.size / 1024).toFixed(1)} KB
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {text ? (
        <>
          <div 
            ref={messageRef}
            className={`${styles.messageContent} ${sender === 'user' ? styles.userMessageContent : styles.aiMessageContent}`}
          >
            <div className={styles.messageText}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={markdownComponents}
              >
                {text}
              </ReactMarkdown>
              {isStreaming && <span className={styles.streamingCursor}>|</span>}
            </div>
            {/* Show image from API if available */}
            {imageDataUrl && (
              <div style={{ marginTop: '1rem' }}>
                <ChartImageRenderer src={imageDataUrl} alt="Chart" />
              </div>
            )}
          </div>
          {showTimestamp && (
            <div className={sender === 'user' ? styles.messageTimeOnly : styles.messageTime}>
              {timestamp}
            </div>
          )}
        </>
      ) : (
        showTimestamp && (
          <div className={styles.messageTimeOnly}>{timestamp}</div>
        )
      )}
      
      {/* Image Preview Modal */}
      {selectedImage && (
        <div className={styles.imagePreviewModal} onClick={() => setSelectedImage(null)}>
          <div className={styles.imagePreviewContent} onClick={(e) => e.stopPropagation()}>
            <button 
              className={styles.imagePreviewClose}
              onClick={() => setSelectedImage(null)}
            >
              <span className="material-icons">close</span>
            </button>
            <img 
              src={selectedImage} 
              alt="Preview" 
              className={styles.imagePreviewLarge}
            />
          </div>
        </div>
      )}
    </div>
  );
};

