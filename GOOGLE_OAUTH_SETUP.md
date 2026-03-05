# Google Sign-In Setup Guide for SadTalker

This guide will help you set up Google Sign-In for your SadTalker application.

## Prerequisites

1. A Google account
2. Access to [Google Cloud Console](https://console.cloud.google.com/)

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top of the page
3. Click "New Project"
4. Enter a project name (e.g., "SadTalker Auth")
5. Click "Create"

## Step 2: Enable Google Sign-In API

1. In your project, go to "APIs & Services" > "Library"
2. Search for "Google Identity Toolkit API" or "Google Sign-In"
3. Click on "Google Identity Toolkit API"
4. Click "Enable"

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Select "External" (for testing with any Google account) or "Internal" (for G Suite users only)
3. Click "Create"
4. Fill in the required fields:
   - **App name**: SadTalker
   - **User support email**: Your email
   - **Developer contact information**: Your email
5. Click "Save and Continue"
6. On the "Scopes" page, click "Add or Remove Scopes"
7. Add these scopes:
   - `openid`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
8. Click "Update" then "Save and Continue"
9. On the "Test users" page, add your email address for testing
10. Click "Save and Continue"
11. Review and click "Back to Dashboard"

## Step 4: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Select "Web application" as the application type
4. Enter a name (e.g., "SadTalker Web Client")
5. Under "Authorized JavaScript origins", add:
   - `http://localhost:5000` (for local development)
   - `http://127.0.0.1:5000` (alternative local address)
   - Your production domain (e.g., `https://yourdomain.com`)
6. Under "Authorized redirect URIs", add:
   - `http://localhost:5000/api/auth/google/callback`
   - Your production callback URL (e.g., `https://yourdomain.com/api/auth/google/callback`)
7. Click "Create"
8. **Important**: Copy the "Client ID" and "Client Secret" - you'll need these!

## Step 5: Configure SadTalker

### Option A: Using Environment Variables (Recommended)

1. Copy the `.env.example` file to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your Google credentials:
   ```env
   GOOGLE_CLIENT_ID=your_actual_client_id_here
   GOOGLE_CLIENT_SECRET=your_actual_client_secret_here
   GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
   ```

### Option B: Direct Configuration

If not using environment variables, edit `api_routes.py`:

```python
GOOGLE_CLIENT_ID = 'your_actual_client_id_here'
GOOGLE_CLIENT_SECRET = 'your_actual_client_secret_here'
GOOGLE_REDIRECT_URI = 'http://localhost:5000/api/auth/google/callback'
```

## Step 6: Update Frontend Google Client ID

Edit `unified_api.html` and replace `YOUR_GOOGLE_CLIENT_ID` with your actual Client ID:

```html
<div id="g_id_onload"
     data-client_id="YOUR_ACTUAL_CLIENT_ID_HERE"
     data-context="signin"
     data-ux_mode="popup"
     data-callback="handleGoogleSignIn"
     data-auto_prompt="false">
</div>
```

## Step 7: Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Or specifically:
```bash
pip install google-auth requests
```

## Step 8: Test the Setup

1. Start your Flask application:
   ```bash
   python app_flask.py
   ```

2. Open your browser to `http://localhost:5000/unified_api.html`

3. You should see a "Sign in with Google" button below the regular login form

4. Click the button and try signing in with your Google account

## Troubleshooting

### "Google OAuth not configured" error
- Make sure you've set the `GOOGLE_CLIENT_ID` environment variable or updated the code directly

### "Invalid token" error
- Check that your Client ID is correct
- Ensure the authorized JavaScript origin matches your URL exactly

### "redirect_uri_mismatch" error
- Go back to Google Cloud Console > Credentials
- Make sure the redirect URI exactly matches your callback URL
- Include the full path: `/api/auth/google/callback`

### Button not appearing
- Check browser console for JavaScript errors
- Ensure the Google Sign-In script is loading: `https://accounts.google.com/gsi/client`
- Verify your Client ID is correctly set in the HTML

## Production Deployment

When deploying to production:

1. Update the authorized JavaScript origins in Google Cloud Console to include your production domain
2. Update the authorized redirect URIs to include your production callback URL
3. Update the `GOOGLE_REDIRECT_URI` environment variable
4. Consider publishing your OAuth consent screen app (move from "Testing" to "In production")
5. Use HTTPS for all URLs

## Security Notes

- Never commit your `GOOGLE_CLIENT_SECRET` to version control
- Keep your `.env` file secure and out of git (it's already in `.gitignore`)
- Use environment variables for all sensitive configuration
- The Client ID can be public (it's in the frontend), but the Client Secret must remain private

## Additional Resources

- [Google Sign-In Documentation](https://developers.google.com/identity/sign-in/web/sign-in)
- [Google OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)