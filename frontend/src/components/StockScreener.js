import React, { useState, useEffect } from 'react';
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
  Alert,
  TableSortLabel
} from '@mui/material';

const StockScreener = () => {
  // Load filters from localStorage or use defaults
  const loadFilters = () => {
    try {
      const saved = localStorage.getItem('screenerFilters');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Failed to load filters from localStorage:', e);
    }
    return {
      min_price: 1,
      max_price: 1000,
      min_volume: 10000,
      min_market_cap: 10000000,  // 10M instead of 100M
      max_market_cap: '',
      patterns: []
    };
  };

  const [filters, setFilters] = useState(loadFilters);
  
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sortBy, setSortBy] = useState('score');
  const [sortOrder, setSortOrder] = useState('desc');
  const [cacheInfo, setCacheInfo] = useState(null);

  const patternOptions = [
    // Original patterns
    { key: 'gap_up', label: 'Gap Up', description: '2%+ gap above previous close' },
    { key: 'breakout', label: 'Breakout', description: 'Breaking above 20-day resistance' },
    { key: 'momentum', label: 'Momentum', description: 'Consecutive higher closes with volume' },
    
    // Advanced reversal patterns
    { key: 'oversold_bounce', label: 'Oversold Bounce', description: 'RSI 25-40 with rising momentum and price stabilization' },
    { key: 'pullback_support', label: 'Pullback to Support', description: 'Healthy pullback to 20-day MA in uptrend' },
    { key: 'volume_accumulation', label: 'Volume Accumulation', description: 'Increasing volume with stable/rising prices' },
    
    // Chart patterns
    { key: 'base_building', label: 'Base Building', description: 'Tight consolidation pattern before potential breakout' },
    { key: 'cup_handle', label: 'Cup & Handle', description: 'Classic cup and handle pattern formation' },
    { key: 'ascending_triangle', label: 'Ascending Triangle', description: 'Rising support with flat resistance' }
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

  // Save filters to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('screenerFilters', JSON.stringify(filters));
    } catch (e) {
      console.warn('Failed to save filters to localStorage:', e);
    }
  }, [filters]);

  // Load cached results if they exist on component mount
  useEffect(() => {
    const loadCachedResults = async () => {
      try {
        // Try to get cached results for current filters
        const response = await axios.post('/api/screen', {
          ...filters,
          max_market_cap: filters.max_market_cap ? parseFloat(filters.max_market_cap) : undefined
        });
        
        if (response.data.from_cache) {
          const screenerResults = response.data.screener_results || [];
          setCacheInfo({
            from_cache: response.data.from_cache,
            cache_date: response.data.cache_date
          });
          
          // Sort results by score (descending) by default
          const sortedResults = screenerResults.sort((a, b) => {
            return (b.score || 0) - (a.score || 0);
          });
          
          setResults(sortedResults);
        }
      } catch (e) {
        // Silently fail - user can manually run screen
        console.log('No cached results available');
      }
    };

    // Only load if we have some meaningful filters set
    if (filters.patterns.length > 0 || filters.min_price > 1 || filters.max_price < 1000) {
      loadCachedResults();
    }
  }, []); // Only run on mount

  const runScreen = async () => {
    setLoading(true);
    setError('');
    setCacheInfo(null);
    try {
      const screenFilters = {
        ...filters,
        max_market_cap: filters.max_market_cap ? parseFloat(filters.max_market_cap) : undefined
      };
      
      const response = await axios.post('/api/screen', screenFilters);
      const screenerResults = response.data.screener_results || [];
      
      // Set cache information
      setCacheInfo({
        from_cache: response.data.from_cache,
        cache_date: response.data.cache_date
      });
      
      // Sort results by score (descending) by default
      const sortedResults = screenerResults.sort((a, b) => {
        if (sortBy === 'score') {
          return sortOrder === 'desc' ? (b.score || 0) - (a.score || 0) : (a.score || 0) - (b.score || 0);
        }
        return 0;
      });
      
      setResults(sortedResults);
    } catch (err) {
      setError('Failed to run screen: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStockClick = (symbol) => {
    // Navigate to the stock analysis page
    window.location.href = `/?symbol=${symbol}`;
  };

  const handleSort = (column) => {
    const newSortOrder = sortBy === column && sortOrder === 'desc' ? 'asc' : 'desc';
    setSortBy(column);
    setSortOrder(newSortOrder);
    
    const sortedResults = [...results].sort((a, b) => {
      let aValue, bValue;
      
      switch (column) {
        case 'score':
          aValue = a.score || 0;
          bValue = b.score || 0;
          break;
        case 'symbol':
          aValue = a.symbol || '';
          bValue = b.symbol || '';
          break;
        case 'price':
          aValue = a.price || 0;
          bValue = b.price || 0;
          break;
        case 'volume':
          aValue = a.volume || 0;
          bValue = b.volume || 0;
          break;
        case 'volume_ratio':
          aValue = a.volume_metrics?.volume_ratio || 0;
          bValue = b.volume_metrics?.volume_ratio || 0;
          break;
        case 'market_cap':
          aValue = a.market_cap || 0;
          bValue = b.market_cap || 0;
          break;
        default:
          return 0;
      }
      
      if (typeof aValue === 'string') {
        return newSortOrder === 'desc' ? bValue.localeCompare(aValue) : aValue.localeCompare(bValue);
      }
      
      return newSortOrder === 'desc' ? bValue - aValue : aValue - bValue;
    });
    
    setResults(sortedResults);
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
              <Grid item xs={12} sm={6} md={4} key={pattern.key}>
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

      {cacheInfo && (
        <Alert 
          severity={cacheInfo.from_cache ? "info" : "success"} 
          sx={{ mb: 2 }}
        >
          {cacheInfo.from_cache 
            ? `⚡ Using cached results from ${cacheInfo.cache_date} (faster loading)`
            : `✨ Fresh screening results for ${cacheInfo.cache_date} (saved for future use)`
          }
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
                    <TableCell>
                      <TableSortLabel
                        active={sortBy === 'symbol'}
                        direction={sortBy === 'symbol' ? sortOrder : 'asc'}
                        onClick={() => handleSort('symbol')}
                      >
                        Symbol
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortBy === 'price'}
                        direction={sortBy === 'price' ? sortOrder : 'desc'}
                        onClick={() => handleSort('price')}
                      >
                        Price
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortBy === 'volume'}
                        direction={sortBy === 'volume' ? sortOrder : 'desc'}
                        onClick={() => handleSort('volume')}
                      >
                        Volume
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortBy === 'volume_ratio'}
                        direction={sortBy === 'volume_ratio' ? sortOrder : 'desc'}
                        onClick={() => handleSort('volume_ratio')}
                      >
                        Vol Ratio
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortBy === 'market_cap'}
                        direction={sortBy === 'market_cap' ? sortOrder : 'desc'}
                        onClick={() => handleSort('market_cap')}
                      >
                        Market Cap
                      </TableSortLabel>
                    </TableCell>
                    <TableCell>Sector</TableCell>
                    <TableCell>Patterns</TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortBy === 'score'}
                        direction={sortBy === 'score' ? sortOrder : 'desc'}
                        onClick={() => handleSort('score')}
                      >
                        Score
                      </TableSortLabel>
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {results.map((stock) => (
                    <TableRow key={stock.symbol}>
                      <TableCell>
                        <Typography 
                          variant="body2" 
                          fontWeight="bold"
                          sx={{ 
                            color: 'primary.main', 
                            cursor: 'pointer',
                            '&:hover': { 
                              textDecoration: 'underline',
                              color: 'primary.dark'
                            }
                          }}
                          onClick={() => handleStockClick(stock.symbol)}
                        >
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
                          {stock.sector ? stock.sector.split(' ').slice(0, 3).join(' ') : 'Unknown'}
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
                      <TableCell align="right">
                        <Chip
                          label={stock.score || 0}
                          color={stock.score >= 20 ? 'success' : stock.score >= 10 ? 'warning' : 'default'}
                          size="small"
                          sx={{ fontWeight: 'bold' }}
                        />
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