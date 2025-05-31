import React, { useState } from 'react';
import axios from 'axios';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControlLabel,
  Checkbox,
  CircularProgress,
  Alert
} from '@mui/material';

const StockScreener = () => {
  const [filters, setFilters] = useState({
    min_price: 1,
    max_price: 1000,
    min_volume: 10000,
    min_market_cap: 10000000,  // 10M instead of 100M
    max_market_cap: '',
    patterns: []
  });
  
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const patternOptions = [
    { key: 'gap_up', label: 'Gap Up', description: '2%+ gap above previous close' },
    { key: 'breakout', label: 'Breakout', description: 'Breaking above 20-day resistance' },
    { key: 'momentum', label: 'Momentum', description: 'Consecutive higher closes with volume' }
  ];

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handlePatternToggle = (pattern) => {
    setFilters(prev => ({
      ...prev,
      patterns: prev.patterns.includes(pattern)
        ? prev.patterns.filter(p => p !== pattern)
        : [...prev.patterns, pattern]
    }));
  };

  const runScreen = async () => {
    setLoading(true);
    setError('');
    try {
      const screenFilters = {
        ...filters,
        max_market_cap: filters.max_market_cap ? parseFloat(filters.max_market_cap) : undefined
      };
      
      const response = await axios.post('/api/screen', screenFilters);
      setResults(response.data.screener_results || []);
    } catch (err) {
      setError('Failed to run screen: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatMarketCap = (marketCap) => {
    if (marketCap >= 1e9) return `$${(marketCap / 1e9).toFixed(1)}B`;
    if (marketCap >= 1e6) return `$${(marketCap / 1e6).toFixed(1)}M`;
    return `$${marketCap.toLocaleString()}`;
  };

  const formatVolume = (volume) => {
    if (volume >= 1e6) return `${(volume / 1e6).toFixed(1)}M`;
    if (volume >= 1e3) return `${(volume / 1e3).toFixed(1)}K`;
    return volume.toLocaleString();
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Stock Screener
      </Typography>
      
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Screening Filters
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                label="Min Price ($)"
                type="number"
                value={filters.min_price}
                onChange={(e) => handleFilterChange('min_price', parseFloat(e.target.value))}
                fullWidth
                margin="normal"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Max Price ($)"
                type="number"
                value={filters.max_price}
                onChange={(e) => handleFilterChange('max_price', parseFloat(e.target.value))}
                fullWidth
                margin="normal"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Min Volume"
                type="number"
                value={filters.min_volume}
                onChange={(e) => handleFilterChange('min_volume', parseInt(e.target.value))}
                fullWidth
                margin="normal"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Min Market Cap ($)"
                type="number"
                value={filters.min_market_cap}
                onChange={(e) => handleFilterChange('min_market_cap', parseFloat(e.target.value))}
                fullWidth
                margin="normal"
              />
            </Grid>
          </Grid>

          <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>
            Pattern Filters
          </Typography>
          
          <Grid container spacing={1}>
            {patternOptions.map(pattern => (
              <Grid item xs={12} md={4} key={pattern.key}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={filters.patterns.includes(pattern.key)}
                      onChange={() => handlePatternToggle(pattern.key)}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {pattern.label}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {pattern.description}
                      </Typography>
                    </Box>
                  }
                />
              </Grid>
            ))}
          </Grid>

          <Button
            variant="contained"
            onClick={runScreen}
            disabled={loading}
            sx={{ mt: 2 }}
            startIcon={loading ? <CircularProgress size={20} /> : null}
          >
            {loading ? 'Screening...' : 'Run Screen'}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {results.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Screening Results ({results.length} stocks)
            </Typography>
            
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Symbol</TableCell>
                    <TableCell align="right">Price</TableCell>
                    <TableCell align="right">Volume</TableCell>
                    <TableCell align="right">Vol Ratio</TableCell>
                    <TableCell align="right">Market Cap</TableCell>
                    <TableCell>Sector</TableCell>
                    <TableCell>Patterns</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {results.map((stock) => (
                    <TableRow key={stock.symbol}>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          {stock.symbol}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">${stock.price}</TableCell>
                      <TableCell align="right">{formatVolume(stock.volume)}</TableCell>
                      <TableCell align="right">
                        <Chip
                          label={`${stock.volume_metrics.volume_ratio}x`}
                          color={stock.volume_metrics.volume_spike ? 'warning' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="right">{formatMarketCap(stock.market_cap)}</TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {stock.sector.split(' ').slice(0, 3).join(' ')}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                          {stock.patterns.map(pattern => (
                            <Chip
                              key={pattern}
                              label={pattern.replace('_', ' ')}
                              color="primary"
                              size="small"
                            />
                          ))}
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default StockScreener;