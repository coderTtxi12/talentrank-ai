// POST /api/v1/chat — must match backend ChatRequest (session_id + message only).
export interface ChatRequestBody {
  session_id: string;
  message: string;
}

// Types para mensajes
export interface Message {
  id: number;
  text: string;
  sender: 'user' | 'ai';
  timestamp: string;
  files?: File[];
  isStreaming?: boolean;
  imageBase64?: string;  // Base64 encoded image from API
  imageMime?: string;    // MIME type of the image
}

// Props para componentes
export interface HeaderProps {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  onClearChat: () => void;
}

export interface WelcomeSectionProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onOpenFileDialog: () => void;
  selectedFiles: File[];
  onRemoveFile: (index: number) => void;
}

export interface MessageListProps extends WelcomeSectionProps {
  messages: Message[];
  isStreaming: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

export interface MessageProps {
  message: Message;
}

export interface InputFormProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onOpenFileDialog: () => void;
  selectedFiles: File[];
  placeholder?: string;
  className?: string;
}

export interface FilePreviewProps {
  files: File[];
  onRemoveFile: (index: number) => void;
}

// Return types para hooks
export interface UseChatReturn {
  messages: Message[];
  inputValue: string;
  setInputValue: (value: string) => void;
  isLoading: boolean;
  isStreaming: boolean;
  selectedFiles: File[];
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  handleSubmit: (e: React.FormEvent) => Promise<void>;
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  removeFile: (index: number) => void;
  openFileDialog: () => void;
  clearChat: () => void;
}

export interface UseThemeReturn {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
}

