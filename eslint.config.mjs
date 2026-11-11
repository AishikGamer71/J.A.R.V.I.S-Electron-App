import js from '@eslint/js'
import tsParser from '@typescript-eslint/parser'
import tsPlugin from '@typescript-eslint/eslint-plugin'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'

export default [
  js.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true }
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.es2021
      }
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
      'react-hooks': reactHooks
    },
    rules: {
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'off',
      'no-undef': 'off',
      'no-empty': ['warn', { allowEmptyCatch: true }],
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn'
    }
  },
  {
    files: ['src/plugins/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/*', '../*', '@hermes/shared'],
              message: 'Plugins import only @hermes/plugin-sdk (and react).'
            }
          ]
        }
      ]
    }
  },
  {
    files: ['**/*.test.{ts,tsx,mjs}'],
    languageOptions: {
      globals: {
        ...globals.jest,
        ...globals.node
      }
    }
  },
  {
    ignores: [
      'dist/**',
      'release/**',
      'build/**',
      'node_modules/**',
      'storage/**',
      '.system_generated/**'
    ]
  }
]
