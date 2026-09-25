export const env = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  FIREBASE_API_KEY: import.meta.env.VITE_FIREBASE_API_KEY || '',
  // Must match the backend's S3_PUBLIC_ENDPOINT_URL. The backend signs upload
  // URLs against this origin, so if the browser used a different host the
  // signature would not verify.
  S3_PUBLIC_ENDPOINT_URL: import.meta.env.VITE_S3_PUBLIC_ENDPOINT_URL || 'http://localhost:9000',
  S3_BUCKET_NAME: import.meta.env.VITE_S3_BUCKET_NAME || 'sust-eee-resources',
};
