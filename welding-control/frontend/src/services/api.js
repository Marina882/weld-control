import axios from 'axios';

const BACKEND_URL = '/api';

export const uploadImage = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const response = await axios.post(`${BACKEND_URL}/analyze/image`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  } catch (error) {
    console.error('Ошибка при анализе изображения:', error);
    throw error;
  }
};

export const analyzeVideoFrame = async (frameData) => {
  try {
    const response = await axios.post(`${BACKEND_URL}/analyze/frame`, { frame: frameData });
    return response.data;
  } catch (error) {
    console.error('Ошибка при анализе кадра:', error);
    throw error;
  }
};

export const generateReport = async (results, format = 'pdf', metadata = {}) => {
  try {
    const response = await axios.post(`${BACKEND_URL}/report/generate`, {
      results,
      format,
      metadata
    });
    return response.data;
  } catch (error) {
    console.error('Ошибка при генерации отчёта:', error);
    throw error;
  }
};

export const checkMLStatus = async () => {
  try {
    const response = await axios.get(`${BACKEND_URL}/analysis/status`);
    return response.data;
  } catch (error) {
    console.error('Ошибка при проверке статуса:', error);
    throw error;
  }
};

export const getReportsList = async () => {
  try {
    const response = await axios.get(`${BACKEND_URL}/report/list`);
    return response.data;
  } catch (error) {
    console.error('Ошибка при получении списка отчётов:', error);
    throw error;
  }
};