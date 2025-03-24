import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  Box, 
  Container, 
  Typography, 
  Paper,
  CircularProgress,
  Button,
  Grid,
  Divider,
  List,
  ListItem,
  ListItemText,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import StopIcon from '@mui/icons-material/Stop'

const modelPaths = {
  'doctor-patient': 'my_model.keras',
  'teacher-student': 'my_model.keras',
  
};

const SessionReport = ({ report }) => {
  if (!report) return null;

  return (
    <Box>
      <List>
        <ListItem>
          <ListItemText 
            primary="Session Duration" 
            secondary={`${report.duration} minutes`}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText 
            primary="Dominant Emotion" 
            secondary={report.dominantEmotion || 'None detected'}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText 
            primary="Total Detections" 
            secondary={report.totalDetections}
          />
        </ListItem>
        <Divider />
        <ListItem>
          <ListItemText 
            primary="Emotion Breakdown"
            secondary={
              <Box sx={{ mt: 1 }}>
                {Object.entries(report.emotionPercentages || {}).map(([emotion, percentage]) => (
                  <Typography key={emotion} variant="body2">
                    {emotion}: {percentage}% ({report.emotionBreakdown[emotion]} times)
                  </Typography>
                ))}
              </Box>
            }
          />
        </ListItem>
      </List>
    </Box>
  );
};

export default function EmotionDetection() {
  const { modelId } = useParams()
  const navigate = useNavigate()
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState(null)
  const [isTracking, setIsTracking] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [sessionReport, setSessionReport] = useState(null)

  useEffect(() => {
    const connectToBackend = async () => {
      try {
        const response = await fetch(`http://localhost:5005/load-model`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({
            modelPath: modelPaths[modelId]
          })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Failed to load model')
        }
        
        setIsConnected(true)
      } catch (err) {
        setError(err.message)
        setIsConnected(false)
      }
    }

    connectToBackend()
  }, [modelId])

  const startTracking = async () => {
    try {
      const response = await fetch('http://localhost:5005/start-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ modelType: modelId })  // Add modelType to request
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to start session');
      }
      
      const data = await response.json();
      setSessionId(data.sessionId);
      setIsTracking(true);
      setSessionReport(null);
    } catch (err) {
      setError(err.message);
    }
  }

  // Move stopTracking to useCallback to prevent unnecessary recreations
  const stopTracking = useCallback(async () => {
    try {
      if (!sessionId) return;
      
      const response = await fetch('http://localhost:5005/stop-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ sessionId })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to stop session');
      }
      
      const data = await response.json();
      setSessionReport(data);
      setIsTracking(false);
      setSessionId(null);
    } catch (err) {
      setError(err.message);
    }
  }, [sessionId]);

  // Cleanup effect
  useEffect(() => {
    return () => {
      if (isTracking && sessionId) {
        stopTracking();
      }
    };
  }, [stopTracking, isTracking, sessionId]);

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate('/')}
        sx={{ mb: 2 }}
      >
        Back to Model Selection
      </Button>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
              {modelId.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join('/')} Emotion Detection
            </Typography>

            {error && (
              <Typography color="error" sx={{ mb: 2 }}>
                Error: {error}
              </Typography>
            )}

            {isConnected && (
              <>
                <Box sx={{ mb: 2 }}>
                  <Button
                    variant="contained"
                    color={isTracking ? "error" : "primary"}
                    startIcon={isTracking ? <StopIcon /> : <PlayArrowIcon />}
                    onClick={isTracking ? stopTracking : startTracking}
                  >
                    {isTracking ? "Stop Tracking" : "Start Tracking"}
                  </Button>
                </Box>

                <Box
                  sx={{
                    width: '100%',
                    maxWidth: 800,
                    height: 600,
                    margin: '0 auto',
                    position: 'relative',
                    overflow: 'hidden',
                    borderRadius: 2,
                    boxShadow: 3
                  }}
                >
                  {isTracking && (
                    <img 
                      src={`http://localhost:5005/video_feed?session_id=${sessionId}&model_type=${modelId}`}
                      alt="Emotion Detection Feed"
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  )}
                </Box>
              </>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Session Report
            </Typography>
            {isTracking ? (
              <Typography variant="body2" color="text.secondary">
                Session in progress...
              </Typography>
            ) : sessionReport ? (
              <SessionReport report={sessionReport} />
            ) : (
              <Typography variant="body2" color="text.secondary">
                No session report available. Start tracking to generate a report.
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}
