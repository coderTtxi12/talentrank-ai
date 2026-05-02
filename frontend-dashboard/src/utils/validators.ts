/**
 * Document validation utilities for different countries.
 */

/**
 * Validate Spanish DNI/NIE.
 * DNI format: 8 digits + 1 letter
 * NIE format: X/Y/Z + 7 digits + 1 letter
 */
export const validateDNI = (value: string): boolean => {
  const dni = value.toUpperCase().replace(/\s/g, '');
  
  // DNI pattern: 8 digits + letter
  const dniPattern = /^[0-9]{8}[A-Z]$/;
  // NIE pattern: X/Y/Z + 7 digits + letter
  const niePattern = /^[XYZ][0-9]{7}[A-Z]$/;
  
  if (!dniPattern.test(dni) && !niePattern.test(dni)) {
    return false;
  }
  
  // Calculate check letter
  const letters = 'TRWAGMYFPDXBNJZSQVHLCKE';
  let number: number;
  
  if (niePattern.test(dni)) {
    // Convert NIE prefix to number
    const prefix = dni.charAt(0);
    const nieNumber = dni.substring(1, 8);
    const prefixMap: Record<string, string> = { X: '0', Y: '1', Z: '2' };
    number = parseInt(prefixMap[prefix] + nieNumber, 10);
  } else {
    number = parseInt(dni.substring(0, 8), 10);
  }
  
  const expectedLetter = letters[number % 23];
  return dni.charAt(dni.length - 1) === expectedLetter;
};

/**
 * Validate Mexican CURP.
 * Format: 18 characters - AAAA000000HSSSCCX0
 */
export const validateCURP = (value: string): boolean => {
  const curp = value.toUpperCase().replace(/\s/g, '');
  
  // Basic format validation
  const pattern = /^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$/;
  
  if (!pattern.test(curp)) {
    return false;
  }
  
  // Validate birth date portion (positions 4-10: YYMMDD)
  const month = parseInt(curp.substring(6, 8), 10);
  const day = parseInt(curp.substring(8, 10), 10);
  
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    return false;
  }
  
  // Validate state code (positions 11-13)
  const validStates = [
    'AS', 'BC', 'BS', 'CC', 'CL', 'CM', 'CS', 'CH', 'DF', 'DG',
    'GT', 'GR', 'HG', 'JC', 'MC', 'MN', 'MS', 'NT', 'NL', 'OC',
    'PL', 'QT', 'QR', 'SP', 'SL', 'SR', 'TC', 'TS', 'TL', 'VZ',
    'YN', 'ZS', 'NE'
  ];
  
  const stateCode = curp.substring(11, 13);
  return validStates.includes(stateCode);
};

/**
 * Get validator function by country code.
 */
export const getDocumentValidator = (countryCode: string): ((value: string) => boolean) => {
  const validators: Record<string, (value: string) => boolean> = {
    ES: validateDNI,
    MX: validateCURP,
  };
  
  return validators[countryCode] || (() => true);
};

/**
 * Get document type by country code.
 */
export const getDocumentType = (countryCode: string): string => {
  const types: Record<string, string> = {
    ES: 'DNI',
    MX: 'CURP',
  };
  
  return types[countryCode] || 'ID';
};

/**
 * Get document placeholder by country code.
 */
export const getDocumentPlaceholder = (countryCode: string): string => {
  const placeholders: Record<string, string> = {
    ES: '12345678A',
    MX: 'AAAA000000HSSSCCX0',
  };
  
  return placeholders[countryCode] || 'Document number';
};

/**
 * Get currency by country code.
 */
export const getCurrency = (countryCode: string): string => {
  const currencies: Record<string, string> = {
    ES: 'EUR',
    MX: 'MXN',
  };
  
  return currencies[countryCode] || 'USD';
};

export default {
  validateDNI,
  validateCURP,
  getDocumentValidator,
  getDocumentType,
  getDocumentPlaceholder,
  getCurrency,
};
