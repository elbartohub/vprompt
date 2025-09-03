export default [
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        setTimeout: 'readonly',
        clearInterval: 'readonly',
        setInterval: 'readonly',
        localStorage: 'readonly',
        FormData: 'readonly',
        FileReader: 'readonly',
        XMLHttpRequest: 'readonly',
        Event: 'readonly',
        CustomEvent: 'readonly',
        alert: 'readonly',
        navigator: 'readonly',
        location: 'readonly',
        Image: 'readonly',
        URL: 'readonly',
        DataTransfer: 'readonly',
        MutationObserver: 'readonly',
        showNotification: 'readonly',
        heic2any: 'readonly'
      }
    },
    rules: {
      'no-unused-vars': 'warn',
      'no-undef': 'error',
      'semi': ['error', 'always'],
      'quotes': ['error', 'double'],
      'indent': ['error', 4]
    }
  }
];
