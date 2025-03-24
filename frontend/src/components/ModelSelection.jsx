import {
  Box,
  Container,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Typography,
  Button,
} from '@mui/material'
import { useNavigate } from 'react-router-dom'

const models = [
  {
    id: 'doctor-patient',
    title: 'Doctor/Patient',
    description: 'Emotion detection for healthcare interactions',
    image: 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=500',
  },
  {
    id: 'teacher-student',
    title: 'Teacher/Student',
    description: 'Emotion detection for educational environments',
    image: 'https://images.unsplash.com/photo-1523580494863-6f3031224c94?auto=format&fit=crop&w=500',
  }
];

export default function ModelSelection() {
  const navigate = useNavigate();

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography 
        variant="h4" 
        align="center" 
        gutterBottom
        sx={{ mb: 4, fontWeight: 500 }}
      >
        Select Emotion Detection Model
      </Typography>
      <Grid container spacing={4} justifyContent="center">
        {models.map((model) => (
          <Grid item xs={12} md={6} key={model.id}>
            <Card 
              sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'scale(1.02)',
                  boxShadow: 6
                }
              }}
            >
              <CardMedia
                component="img"
                height="250"
                image={model.image}
                alt={model.title}
                sx={{ objectFit: 'cover' }}
              />
              <CardContent sx={{ flexGrow: 1, textAlign: 'center' }}>
                <Typography gutterBottom variant="h5" component="div" sx={{ fontWeight: 500 }}>
                  {model.title}
                </Typography>
                <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                  {model.description}
                </Typography>
                <Button
                  variant="contained"
                  size="large"
                  fullWidth
                  onClick={() => navigate(`/detection/${model.id}`)}
                  sx={{
                    mt: 2,
                    backgroundColor: '#2c3e50',
                    '&:hover': {
                      backgroundColor: '#34495e'
                    }
                  }}
                >
                  Select Model
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}