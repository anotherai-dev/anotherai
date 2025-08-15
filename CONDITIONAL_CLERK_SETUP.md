# Conditional Clerk Authentication Setup

This implementation provides optional Clerk authentication that can be enabled/disabled based on environment variables.

## How it works

1. **Environment Variable Control**: Authentication is controlled by the `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` environment variable
2. **Graceful Fallback**: When Clerk is disabled or unavailable, the app falls back to no authentication (always signed in)
3. **Dynamic Loading**: Clerk components are loaded dynamically to avoid build errors when the package isn't installed

## Setup Instructions

### To Enable Clerk Authentication:

1. **Install the Clerk package:**
   ```bash
   cd web
   npm install @clerk/nextjs
   ```

2. **Set environment variables in `.env`:**
   ```bash
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
   CLERK_SECRET_KEY=sk_test_your_key_here
   ```

3. **Get Clerk keys from https://dashboard.clerk.com/**

### To Disable Clerk Authentication:

1. **Comment out or remove the `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` in `.env`:**
   ```bash
   # NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
   ```

2. **The app will automatically fall back to no authentication**

## Implementation Details

### Auth Components
All auth components in `/web/src/components/auth/` are designed to:
- Check for `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` 
- Try to load Clerk components dynamically when enabled
- Fall back to appropriate default behavior when disabled:
  - `SignedIn`: Always shows content (users always signed in)
  - `SignedOut`: Never shows content (users never signed out)
  - `UserButton`: Shows static "User" button
  - `SignIn/SignUp`: Redirect to home page
  - `SignInButton/SignUpButton`: Pass through children without auth

### Middleware
The middleware in `/web/src/middleware.ts`:
- Passes through all requests when Clerk is disabled
- Uses Clerk middleware when enabled and package is available

### Environment Configuration
- `.env.example` includes Clerk configuration documentation
- Current `.env` has Clerk keys but they're commented out by default

## Current Status
- ✅ All auth components implement conditional logic
- ✅ Build succeeds with or without Clerk package
- ✅ Graceful fallback when Clerk unavailable
- ✅ Environment variable control working
- ⚠️  Clerk package currently not installed (to avoid build issues)

## Testing
To test the implementation:
1. **With Clerk disabled**: App works normally, users always signed in
2. **With Clerk enabled**: Install package, set env vars, get full auth functionality