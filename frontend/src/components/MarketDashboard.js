import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Alert
} from '@mui/material';
import { TrendingUp, TrendingDown, TrendingFlat } from '@mui/icons-material';

const MarketDashboard = () => {
  const [marketData, setMarketData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchMarketData();
  }, []);

  const fetchMarketData = async () => {
    try {
      const response = await axios.get('/api/market/context');
      setMarketData(response.data.market_context);
    } catch (err) {
      setError('Failed to load market data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getRegimeColor = (regime) => {
    switch (regime) {
      case 'BULL_TREND': return 'success';
      case 'RISK_ON': return 'success';
      case 'RISK_OFF': return 'error';
      case 'UNCERTAIN': return 'warning';
      default: return 'default';
    }
  };

  const getPerformanceIcon = (performance) => {
    if (performance > 1) return <TrendingUp color="success" />;
    if (performance < -1) return <TrendingDown color="error" />;
    return <TrendingFlat color="action" />;
  };

  const getPerformanceColor = (performance) => {
    if (performance > 2) return 'success';
    if (performance < -2) return 'error';
    return 'default';
  };

  if (loading) return <LinearProgress />;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!marketData) return null;

  const { regime, regime_signals, breadth, sector_performance, sectors_advancing } = marketData;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Market Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Market Regime */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Market Regime
              </Typography>
              <Chip
                label={regime.replace('_', ' ')}
                color={getRegimeColor(regime)}
                size="large"
                sx={{ mb: 2 }}
              />
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Supporting Signals:
                </Typography>
                {regime_signals.map((signal, index) => (
                  <Typography key={index} variant="body2" color="text.secondary">
                    • {signal}
                  </Typography>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Market Breadth */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Market Breadth
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    SPY Price
                  </Typography>
                  <Typography variant="h6">
                    ${breadth.spy_price}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    VIX Level
                  </Typography>
                  <Typography variant="h6">
                    {breadth.vix}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    vs 20-day SMA
                  </Typography>
                  <Typography 
                    variant="body1" 
                    color={breadth.spy_vs_sma20 > 0 ? 'success.main' : 'error.main'}
                  >
                    {breadth.spy_vs_sma20 > 0 ? '+' : ''}{breadth.spy_vs_sma20}%
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    vs 50-day SMA
                  </Typography>
                  <Typography 
                    variant="body1" 
                    color={breadth.spy_vs_sma50 > 0 ? 'success.main' : 'error.main'}
                  >
                    {breadth.spy_vs_sma50 > 0 ? '+' : ''}{breadth.spy_vs_sma50}%
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Sector Performance */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Sector Performance & Rotation
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Sectors Advancing: {sectors_advancing}
              </Typography>
              
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Sector</TableCell>
                      <TableCell>ETF</TableCell>
                      <TableCell align="right">1D %</TableCell>
                      <TableCell align="right">5D %</TableCell>
                      <TableCell align="right">20D %</TableCell>
                      <TableCell align="right">Rel Strength</TableCell>
                      <TableCell>Trend</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(sector_performance)
                      .sort(([,a], [,b]) => b.performance_20d - a.performance_20d)
                      .map(([sector, data]) => (
                      <TableRow key={sector}>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {sector}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {data.symbol}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography 
                            variant="body2" 
                            color={getPerformanceColor(data.performance_1d) + '.main'}
                          >
                            {data.performance_1d > 0 ? '+' : ''}{data.performance_1d}%
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography 
                            variant="body2" 
                            color={getPerformanceColor(data.performance_5d) + '.main'}
                          >
                            {data.performance_5d > 0 ? '+' : ''}{data.performance_5d}%
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography 
                            variant="body2" 
                            color={getPerformanceColor(data.performance_20d) + '.main'}
                          >
                            {data.performance_20d > 0 ? '+' : ''}{data.performance_20d}%
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={`${data.relative_strength > 0 ? '+' : ''}${data.relative_strength}%`}
                            color={data.relative_strength > 0 ? 'success' : 'error'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          {getPerformanceIcon(data.performance_20d)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default MarketDashboard;