'use client';

import React, { useState, useEffect } from 'react';
import { FilePreviewProps } from '@/types';
import styles from './FilePreview.module.css';

const getFileIcon = (file: File): string => {
  const type = file.type;
  if (type.startsWith('image/')) return 'image';
  if (type.startsWith('video/')) return 'movie';
  if (type.startsWith('audio/')) return 'audiotrack';
  if (type.includes('pdf')) return 'picture_as_pdf';
  if (type.includes('word') || type.includes('document')) return 'description';
  if (type.includes('excel') || type.includes('spreadsheet')) return 'table_chart';
  if (type.includes('powerpoint') || type.includes('presentation')) return 'slideshow';
  if (type.includes('zip') || type.includes('rar')) return 'folder_zip';
  return 'insert_drive_file';
};

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const createThumbnail = (file: File): Promise<string | null> => {
  return new Promise((resolve) => {
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.readAsDataURL(file);
    } else {
      resolve(null);
    }
  });
};

interface FileThumbnailProps {
  file: File;
  index: number;
  onRemove: () => void;
}

const FileThumbnail: React.FC<FileThumbnailProps> = ({ file, onRemove }) => {
  const [thumbnail, setThumbnail] = useState<string | null>(null);

  useEffect(() => {
    createThumbnail(file).then(setThumbnail);
  }, [file]);

  return (
    <div className={styles.fileThumbnail}>
      <div className={styles.fileThumbnailContent}>
        {thumbnail ? (
          <img src={thumbnail} alt={file.name} className={styles.fileThumbnailImage} />
        ) : (
          <div className={styles.fileThumbnailIcon}>
            <span className="material-icons">{getFileIcon(file)}</span>
          </div>
        )}
        <div className={styles.fileThumbnailInfo}>
          <div className={styles.fileName} title={file.name}>
            {file.name.length > 15 ? `${file.name.substring(0, 15)}...` : file.name}
          </div>
          <div className={styles.fileSize}>{formatFileSize(file.size)}</div>
        </div>
      </div>
      <button 
        className={styles.removeFileBtn}
        onClick={onRemove}
        title="Remove file"
      >
        <span className="material-icons">close</span>
      </button>
    </div>
  );
};

export const FilePreview: React.FC<FilePreviewProps> = ({ files, onRemoveFile }) => {
  if (!files || files.length === 0) return null;

  return (
    <div className={styles.filePreviewContainer}>
      <div className={styles.filePreviewList}>
        {files.map((file, index) => (
          <FileThumbnail
            key={`${file.name}-${index}`}
            file={file}
            index={index}
            onRemove={() => onRemoveFile(index)}
          />
        ))}
      </div>
    </div>
  );
};

