import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import CICDDashboard from './components/CICDDashboard';
import CodegenExample from './components/CodegenExample';
import { WebSocketProvider } from './hooks/useWebSocket';
import darkTheme from './theme/darkTheme';

function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <WebSocketProvider>
        <Router>
          <Routes>
            <Route path="/" element={<CICDDashboard />} />
            <Route path="/codegen-example" element={<CodegenExample />} />
          </Routes>
        </Router>
      </WebSocketProvider>
    </ThemeProvider>
  );
}

export default App;
