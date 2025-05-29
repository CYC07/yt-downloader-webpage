// src/main.jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx'; // Imports the simplified App
// You might have an index.css import here - that's fine
import './index.css';

console.log("--- Running main.jsx ---"); // Add a console log

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);