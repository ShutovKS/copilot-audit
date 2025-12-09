import axios from 'axios';
import { useAppStore } from '../../entities/store';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
    const sessionId = useAppStore.getState().sessionId;
    if (sessionId) {
        config.headers['X-Session-ID'] = sessionId;
    }
    return config;
});

export const generateTest = async (userRequest: string, modelName: string) => {
  const response = await api.post('/generate', { user_request: userRequest, model_name: modelName });
  return response.data;
};

export const exportToGitLab = async (code: string, projectId: string, token: string, url: string) => {
  const response = await api.post('/export/gitlab', { 
      code, 
      project_id: projectId, 
      token, 
      url 
  });
  return response.data;
};

export const analyzeSourceCode = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/analyze-source', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    });
    return response.data;
};

export const analyzeGitRepo = async (url: string, token?: string) => {
    const response = await api.post('/analyze-git', { url, token });
    return response.data;
};
