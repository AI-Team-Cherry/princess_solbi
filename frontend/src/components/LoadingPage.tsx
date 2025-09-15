import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';

const LoadingPage: React.FC = () => {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        gap: 2,
      }}
    >
      <CircularProgress size={60} />
      <Typography variant="h6" color="text.secondary">
        로딩 중...
      </Typography>
    </Box>
  );
};

export default LoadingPage;