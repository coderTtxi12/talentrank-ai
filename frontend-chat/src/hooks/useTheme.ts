'use client';

import { useState, useEffect } from 'react';
import { UseThemeReturn } from '@/types';

export const useTheme = (): UseThemeReturn => {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [mounted, setMounted] = useState(false);

  // Evitar hydration mismatch
  useEffect(() => {
    setMounted(true);
    const savedTheme = localStorage.getItem('theme') as 'dark' | 'light';
    // Si no hay tema guardado, usar 'dark' por defecto
    if (savedTheme) {
      setTheme(savedTheme);
    } else {
      // Establecer 'dark' como predeterminado si no hay tema guardado
      setTheme('dark');
      localStorage.setItem('theme', 'dark');
    }
  }, []);

  useEffect(() => {
    if (mounted) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);
    }
  }, [theme, mounted]);

  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'dark' ? 'light' : 'dark');
  };

  return { theme, toggleTheme };
};

