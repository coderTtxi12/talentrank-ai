import type { Metadata } from 'next';
import './globals.css';
import {
  CHAT_METADATA_DESCRIPTION,
  CHAT_METADATA_TITLE,
} from '@/constants/branding';

export const metadata: Metadata = {
  title: CHAT_METADATA_TITLE,
  description: CHAT_METADATA_DESCRIPTION,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" data-theme="dark">
      <head>
        <link 
          href="https://fonts.googleapis.com/icon?family=Material+Icons" 
          rel="stylesheet" 
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
