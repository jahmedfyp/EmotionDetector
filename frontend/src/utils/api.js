import axios from 'axios';

const PYTHON_API_URL = import.meta.env.VITE_PYTHON_API_URL;

export const pythonApi = axios.create({
  baseURL: PYTHON_API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'
  },
  withCredentials: false
});

export const checkPythonServer = async () => {
  try {
    const response = await pythonApi.get('/status');
    return response.data.status === 'running';
  } catch (error) {
    console.error('Python server check failed:', error);
    return false;
  }
};