import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_URL,
});

export const generateTest = async (userRequest: string) => {
  const response = await api.post('/generate', { user_request: userRequest });
  return response.data;
};
