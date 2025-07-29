import { createTheme } from '@mui/material/styles';

// Dark theme color palette
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
      dark: '#42a5f5',
      light: '#e3f2fd',
    },
    secondary: {
      main: '#f48fb1',
      dark: '#e91e63',
      light: '#fce4ec',
    },
    background: {
      default: '#0a0a0a',
      paper: '#1a1a1a',
    },
    surface: {
      main: '#2a2a2a',
      light: '#3a3a3a',
      dark: '#1a1a1a',
    },
    text: {
      primary: '#ffffff',
      secondary: '#b0b0b0',
    },
    success: {
      main: '#4caf50',
      dark: '#388e3c',
      light: '#c8e6c9',
    },
    error: {
      main: '#f44336',
      dark: '#d32f2f',
      light: '#ffcdd2',
    },
    warning: {
      main: '#ff9800',
      dark: '#f57c00',
      light: '#ffe0b2',
    },
    info: {
      main: '#2196f3',
      dark: '#1976d2',
      light: '#bbdefb',
    },
    divider: '#333333',
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
      color: '#ffffff',
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
      color: '#ffffff',
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
      color: '#ffffff',
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
      color: '#ffffff',
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
      color: '#ffffff',
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
      color: '#ffffff',
    },
    body1: {
      fontSize: '1rem',
      color: '#ffffff',
    },
    body2: {
      fontSize: '0.875rem',
      color: '#b0b0b0',
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#0a0a0a',
          color: '#ffffff',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#1a1a1a',
          borderBottom: '1px solid #333333',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#1a1a1a',
          border: '1px solid #333333',
          '&:hover': {
            borderColor: '#90caf9',
            boxShadow: '0 4px 20px rgba(144, 202, 249, 0.15)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: '#1a1a1a',
          border: '1px solid #333333',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: '8px',
        },
        contained: {
          backgroundColor: '#90caf9',
          color: '#000000',
          '&:hover': {
            backgroundColor: '#42a5f5',
          },
        },
        outlined: {
          borderColor: '#90caf9',
          color: '#90caf9',
          '&:hover': {
            borderColor: '#42a5f5',
            backgroundColor: 'rgba(144, 202, 249, 0.08)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: '#2a2a2a',
            '& fieldset': {
              borderColor: '#333333',
            },
            '&:hover fieldset': {
              borderColor: '#90caf9',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#90caf9',
            },
          },
          '& .MuiInputLabel-root': {
            color: '#b0b0b0',
            '&.Mui-focused': {
              color: '#90caf9',
            },
          },
          '& .MuiOutlinedInput-input': {
            color: '#ffffff',
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          backgroundColor: '#2a2a2a',
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: '#333333',
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: '#90caf9',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: '#90caf9',
          },
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          backgroundColor: '#1a1a1a',
          color: '#ffffff',
          '&:hover': {
            backgroundColor: '#2a2a2a',
          },
          '&.Mui-selected': {
            backgroundColor: '#90caf9',
            color: '#000000',
            '&:hover': {
              backgroundColor: '#42a5f5',
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          backgroundColor: '#2a2a2a',
          color: '#ffffff',
          border: '1px solid #333333',
        },
        colorSuccess: {
          backgroundColor: '#4caf50',
          color: '#ffffff',
        },
        colorError: {
          backgroundColor: '#f44336',
          color: '#ffffff',
        },
        colorWarning: {
          backgroundColor: '#ff9800',
          color: '#000000',
        },
        colorInfo: {
          backgroundColor: '#2196f3',
          color: '#ffffff',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          backgroundColor: '#2a2a2a',
          border: '1px solid #333333',
        },
        standardSuccess: {
          backgroundColor: '#1b5e20',
          color: '#c8e6c9',
          border: '1px solid #4caf50',
        },
        standardError: {
          backgroundColor: '#b71c1c',
          color: '#ffcdd2',
          border: '1px solid #f44336',
        },
        standardWarning: {
          backgroundColor: '#e65100',
          color: '#ffe0b2',
          border: '1px solid #ff9800',
        },
        standardInfo: {
          backgroundColor: '#0d47a1',
          color: '#bbdefb',
          border: '1px solid #2196f3',
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: '#1a1a1a',
          border: '1px solid #333333',
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          backgroundColor: '#2a2a2a',
          borderBottom: '1px solid #333333',
          color: '#ffffff',
        },
      },
    },
    MuiDialogContent: {
      styleOverrides: {
        root: {
          backgroundColor: '#1a1a1a',
          color: '#ffffff',
        },
      },
    },
    MuiDialogActions: {
      styleOverrides: {
        root: {
          backgroundColor: '#2a2a2a',
          borderTop: '1px solid #333333',
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        root: {
          backgroundColor: '#2a2a2a',
          borderBottom: '1px solid #333333',
        },
        indicator: {
          backgroundColor: '#90caf9',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          color: '#b0b0b0',
          '&.Mui-selected': {
            color: '#90caf9',
          },
        },
      },
    },
    MuiSnackbar: {
      styleOverrides: {
        root: {
          '& .MuiAlert-root': {
            backgroundColor: '#2a2a2a',
            border: '1px solid #333333',
          },
        },
      },
    },
  },
});

// Extend the theme interface to include custom colors
declare module '@mui/material/styles' {
  interface Palette {
    surface: {
      main: string;
      light: string;
      dark: string;
    };
  }

  interface PaletteOptions {
    surface?: {
      main: string;
      light: string;
      dark: string;
    };
  }
}

export default darkTheme;
