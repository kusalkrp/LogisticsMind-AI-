import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
});

export async function sendMessage(userId, message) {
  const response = await api.post('/chat', {
    user_id: userId,
    message: message,
  });
  return response.data;
}

export async function checkHealth() {
  const response = await api.get('/health');
  return response.data;
}
