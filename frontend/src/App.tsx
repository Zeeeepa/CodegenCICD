import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Container, CssBaseline } from '@mui/material';
import { ThemeProvider } from '@mui/material/styles';
import Dashboard from './components/Dashboard';
import { WebSocketProvider } from './hooks/useWebSocket';
import darkTheme from './theme/darkTheme';

function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <WebSocketProvider>
        <Router>
          <Container maxWidth="xl" sx={{ py: 2 }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
            </Routes>
          </Container>
        </Router>
      </WebSocketProvider>
    </ThemeProvider>
  );
}

export default App;
