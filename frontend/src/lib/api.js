import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Cookies (httpOnly auth_token / session_token) are automatically sent by the browser
// due to `withCredentials: true`. No localStorage token handling is used.
const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

export default api;
