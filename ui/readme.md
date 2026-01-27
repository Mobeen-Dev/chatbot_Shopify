# Shopify Extension Setup Guide

This project generates a Shopify extension and replaces the default assets, blocks, and locale files with the contents of this folder.

## Setup Instructions

1. **Generate the Shopify Extension**
   - Create a new Shopify extension using the Shopify CLI.
   - Once generated, replace the following directories with the contents from this repository:
     - `assets`
     - `blocks`
     - `locales`

2. **Build and Run the Extension**
   - Install dependencies if required.
   - Build the extension.
   - Run the extension locally using the Shopify CLI.

3. **Configure Backend Connection**
   - Open the extension **Settings** in the Shopify admin.
   - Configure the **Backend URL** field with your backend service endpoint.

4. **CORS Configuration**
   - Ensure CORS is properly configured on the backend to allow requests from the Shopify extension domain.

5. **Test Communication**
   - Start the backend with a dummy endpoint available at:
     ```
     https://app.domain/test-chat
     ```
   - Verify that the extension can successfully connect and communicate with the backend using this endpoint.

## Notes

- The `/test-chat` endpoint is intended for testing and should return a dummy response.
- Replace `app.domain` with your actual backend domain.
