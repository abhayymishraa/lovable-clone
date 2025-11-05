# API Service Layer

This folder contains the centralized API service layer using Axios for all HTTP requests.

## 📁 Structure

```
api/
├── client.ts    # Axios instance with interceptors
├── types.ts     # TypeScript interfaces for API requests/responses
├── auth.ts      # Authentication API calls
├── chat.ts      # Chat API calls
└── index.ts     # Barrel export for clean imports
```

## 🚀 Usage

### Import the APIs

```typescript
import { authApi, chatApi } from '@/api';
```

### Authentication APIs

```typescript
// Login
const { auth_token, user_data } = await authApi.login({ email, password });

// Register
const { auth_token, user_data } = await authApi.register({ name, email, password });

// Get current user (refresh token count)
const userData = await authApi.getCurrentUser();
```

### Chat APIs

```typescript
#### Create Chat
```typescript
const chat = await chatApi.createChat(chatId, prompt);
```

// Check URL health
const isHealthy = await chatApi.checkUrlHealth(url);
```

## ✨ Features

### Automatic Token Injection
All API calls automatically include the `Authorization: Bearer <token>` header from `localStorage`.

### Global Error Handling
- **401 Unauthorized**: Automatically clears auth data and redirects to `/signin`
- All errors are formatted as Error objects with meaningful messages

### TypeScript Support
Full TypeScript types for all request/response objects.

## 🔧 Configuration

Base URL is configured via environment variable:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

If not set, it defaults to `http://localhost:8000`.

## 🎯 Migration Summary

All API calls have been migrated from native `fetch` to Axios:

### Before (native fetch)
```typescript
const response = await fetch(`${API_URL}/auth/login`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({ email, password }),
});

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail);
}

const data = await response.json();
```

### After (Axios)
```typescript
const data = await authApi.login({ email, password });
```

## 📦 Migrated Files

1. ✅ `/app/signin/page.tsx` - Uses `authApi.login()`
2. ✅ `/app/signup/page.tsx` - Uses `authApi.register()`
3. ✅ `/app/chat/page.tsx` - Uses `authApi.getCurrentUser()` and `chatApi.createChat()`
4. ✅ `/app/chat/[id]/page.tsx` - Already uses WebSocket (no migration needed)

## 🎨 Benefits

1. **Cleaner Code**: Less boilerplate, more readable
2. **Centralized Logic**: All API calls in one place
3. **Better Error Handling**: Automatic retry, timeout, and error formatting
4. **Type Safety**: Full TypeScript support
5. **Maintainability**: Easy to update endpoints or add new features
6. **Automatic Auth**: Token injection handled automatically
7. **Better DX**: Interceptors for logging, debugging, etc.
