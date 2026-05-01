import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Data Analyst Agent',
  description: 'Modern natural language dashboard generator',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="dark">
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
