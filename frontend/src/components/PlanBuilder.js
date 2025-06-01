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
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Divider,
  FormControlLabel,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  IconButton
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';

const PlanBuilder = () => {
  const [planConfig, setPlanConfig] = useState({
    plan_name: '',
    total_capital: 4000,
    risk_percentage: 2.0,
    max_positions: 3,
    filters: {
      min_price: 10,
      max_price: 300,
      min_volume: 500000,
      min_market_cap: 100000000,
      patterns: []  // Start with no pattern restrictions to find stocks
    }
  });

  const [tradingPlan, setTradingPlan] = useState(null);
  const [savedPlans, setSavedPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [viewPlanDialog, setViewPlanDialog] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);

  const patternOptions = [
    { key: 'gap_up', label: 'Gap Up' },
    { key: 'breakout', label: 'Breakout' },
    { key: 'momentum', label: 'Momentum' },
    { key: 'oversold_bounce', label: 'Oversold Bounce' },
    { key: 'pullback_support', label: 'Pullback to Support' },
    { key: 'volume_accumulation', label: 'Volume Accumulation' },
    { key: 'base_building', label: 'Base Building' },
    { key: 'cup_handle', label: 'Cup & Handle' },
    { key: 'ascending_triangle', label: 'Ascending Triangle' }
  ];

  useEffect(() => {
    loadSavedPlans();
  }, []);

  const loadSavedPlans = async () => {
    try {
      const response = await axios.get('/api/plan-builder/plans');
      setSavedPlans(response.data.trading_plans || []);
    } catch (err) {
      console.error('Failed to load saved plans:', err);
    }
  };

  const handleConfigChange = (field, value) => {
    setPlanConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleFilterChange = (field, value) => {
    setPlanConfig(prev => ({
      ...prev,
      filters: {
        ...prev.filters,
        [field]: value
      }
    }));
  };

  const handlePatternToggle = (pattern) => {
    setPlanConfig(prev => ({
      ...prev,
      filters: {
        ...prev.filters,
        patterns: prev.filters.patterns.includes(pattern)
          ? prev.filters.patterns.filter(p => p !== pattern)
          : [...prev.filters.patterns, pattern]
      }
    }));
  };

  const createPlan = async () => {
    if (!planConfig.plan_name.trim()) {
      setError('Plan name is required');
      return;
    }

    setLoading(true);
    setError('');
    setTradingPlan(null);

    try {
      const response = await axios.post('/api/plan-builder/create', planConfig);
      setTradingPlan(response.data.trading_plan);
      loadSavedPlans(); // Refresh saved plans
    } catch (err) {
      if (err.response?.status === 404) {
        setError('No stocks found matching your criteria. Try reducing the pattern filters or adjusting price/volume ranges.');
      } else {
        setError('Failed to create trading plan: ' + (err.response?.data?.detail || err.message));
      }
    } finally {
      setLoading(false);
    }
  };

  const viewPlan = async (planId) => {
    try {
      const response = await axios.get(`/api/plan-builder/plans/${planId}`);
      setSelectedPlan(response.data.trading_plan);
      setViewPlanDialog(true);
    } catch (err) {
      setError('Failed to load plan details');
    }
  };

  const deletePlan = async (planId) => {
    if (!window.confirm('Are you sure you want to delete this plan?')) return;
    
    try {
      await axios.delete(`/api/plan-builder/plans/${planId}`);
      loadSavedPlans();
    } catch (err) {
      setError('Failed to delete plan');
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatPercent = (value) => {
    return `${value.toFixed(2)}%`;
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Plan Builder
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Create comprehensive trading plans with automatic position sizing, risk management, and profit targets
      </Typography>

      {/* Plan Configuration */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Plan Configuration
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                label="Plan Name"
                value={planConfig.plan_name}
                onChange={(e) => handleConfigChange('plan_name', e.target.value)}
                fullWidth
                margin="normal"
                placeholder="e.g., High Momentum Growth Plan"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Total Capital ($)"
                type="number"
                value={planConfig.total_capital}
                onChange={(e) => handleConfigChange('total_capital', parseFloat(e.target.value))}
                fullWidth
                margin="normal"
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="Risk per Position (%)"
                type="number"
                value={planConfig.risk_percentage}
                onChange={(e) => handleConfigChange('risk_percentage', parseFloat(e.target.value))}
                fullWidth
                margin="normal"
                inputProps={{ min: 0.1, max: 10, step: 0.1 }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="Max Positions"
                type="number"
                value={planConfig.max_positions}
                onChange={(e) => handleConfigChange('max_positions', parseInt(e.target.value))}
                fullWidth
                margin="normal"
                inputProps={{ min: 1, max: 20 }}
              />
            </Grid>
          </Grid>

          <Typography variant="h6" sx={{ mt: 3, mb: 2 }}>
            Screening Filters
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={3}>
              <TextField
                label="Min Price ($)"
                type="number"
                value={planConfig.filters.min_price}
                onChange={(e) => handleFilterChange('min_price', parseFloat(e.target.value))}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                label="Max Price ($)"
                type="number"
                value={planConfig.filters.max_price}
                onChange={(e) => handleFilterChange('max_price', parseFloat(e.target.value))}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                label="Min Volume"
                type="number"
                value={planConfig.filters.min_volume}
                onChange={(e) => handleFilterChange('min_volume', parseInt(e.target.value))}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                label="Min Market Cap ($)"
                type="number"
                value={planConfig.filters.min_market_cap}
                onChange={(e) => handleFilterChange('min_market_cap', parseFloat(e.target.value))}
                fullWidth
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
                      checked={planConfig.filters.patterns.includes(pattern.key)}
                      onChange={() => handlePatternToggle(pattern.key)}
                    />
                  }
                  label={pattern.label}
                />
              </Grid>
            ))}
          </Grid>

          <Button
            variant="contained"
            onClick={createPlan}
            disabled={loading}
            sx={{ mt: 3 }}
            startIcon={loading ? <CircularProgress size={20} /> : null}
          >
            {loading ? 'Creating Plan...' : 'Create Trading Plan'}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Generated Trading Plan */}
      {tradingPlan && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Trading Plan: {tradingPlan.plan_name}
            </Typography>

            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} md={3}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" color="primary">
                      {formatCurrency(tradingPlan.capital_info.total_capital)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Capital
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={3}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" color="success.main">
                      {formatCurrency(tradingPlan.capital_info.allocated_capital)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Allocated ({tradingPlan.capital_info.allocation_pct}%)
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={3}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" color="warning.main">
                      {formatPercent(tradingPlan.risk_management.total_risk_pct)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Risk
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={3}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6">
                      {tradingPlan.positions.length}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Positions
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            <Typography variant="h6" gutterBottom>
              Position Details
            </Typography>

            {tradingPlan.positions.map((position, index) => (
              <Accordion key={position.symbol} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                    <Typography variant="h6">{position.symbol}</Typography>
                    <Chip label={`Score: ${position.score}`} color="primary" size="small" />
                    <Typography variant="body2" color="text.secondary">
                      {formatCurrency(position.position_value)} ({position.allocation_pct}%)
                    </Typography>
                    <Typography variant="body2" color="warning.main">
                      Risk: {formatPercent(position.risk_pct)}
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" gutterBottom>Entry Strategy</Typography>
                      <Typography>Current Price: {formatCurrency(position.current_price)}</Typography>
                      <Typography>Suggested Entry: {formatCurrency(position.suggested_entry)}</Typography>
                      <Typography>Shares: {position.shares}</Typography>
                      <Typography>Position Value: {formatCurrency(position.position_value)}</Typography>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle2" gutterBottom>Risk Management</Typography>
                      <Typography>Stop Loss: {formatCurrency(position.stop_loss)}</Typography>
                      <Typography>Risk Amount: {formatCurrency(position.risk_amount)}</Typography>
                      <Typography>Support: {formatCurrency(position.support_level)}</Typography>
                      <Typography>Resistance: {formatCurrency(position.resistance_level)}</Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="subtitle2" gutterBottom>Profit Targets</Typography>
                      <TableContainer component={Paper} variant="outlined">
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Target Price</TableCell>
                              <TableCell>Shares to Sell</TableCell>
                              <TableCell>Allocation %</TableCell>
                              <TableCell>Potential Profit</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {position.targets.map((target, idx) => (
                              <TableRow key={idx}>
                                <TableCell>{formatCurrency(target.price)}</TableCell>
                                <TableCell>{target.shares_to_sell}</TableCell>
                                <TableCell>{target.allocation_pct}%</TableCell>
                                <TableCell>{formatCurrency(target.potential_profit)}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Grid>
                    <Grid item xs={12}>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                        {position.patterns.map(pattern => (
                          <Chip key={pattern} label={pattern.replace('_', ' ')} size="small" />
                        ))}
                      </Box>
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Saved Plans */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Saved Trading Plans
          </Typography>
          
          {savedPlans.length === 0 ? (
            <Typography color="text.secondary">
              No saved plans yet. Create your first trading plan above.
            </Typography>
          ) : (
            <List>
              {savedPlans.map((plan) => (
                <ListItem key={plan.id} sx={{ border: 1, borderColor: 'divider', mb: 1, borderRadius: 1 }}>
                  <ListItemText
                    primary={plan.plan_name}
                    secondary={
                      <Box>
                        <Typography variant="body2">
                          Capital: {formatCurrency(plan.total_capital)} | 
                          Positions: {plan.num_positions} | 
                          Risk: {formatPercent(plan.total_risk)} | 
                          Created: {new Date(plan.created_date).toLocaleDateString()}
                        </Typography>
                      </Box>
                    }
                  />
                  <IconButton onClick={() => viewPlan(plan.id)} color="primary">
                    <VisibilityIcon />
                  </IconButton>
                  <IconButton onClick={() => deletePlan(plan.id)} color="error">
                    <DeleteIcon />
                  </IconButton>
                </ListItem>
              ))}
            </List>
          )}
        </CardContent>
      </Card>

      {/* Plan Details Dialog */}
      <Dialog open={viewPlanDialog} onClose={() => setViewPlanDialog(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          {selectedPlan?.plan_name}
        </DialogTitle>
        <DialogContent>
          {selectedPlan && (
            <Box>
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={3}>
                  <Typography variant="subtitle2">Total Capital</Typography>
                  <Typography variant="h6">{formatCurrency(selectedPlan.capital_info.total_capital)}</Typography>
                </Grid>
                <Grid item xs={3}>
                  <Typography variant="subtitle2">Allocated</Typography>
                  <Typography variant="h6">{formatCurrency(selectedPlan.capital_info.allocated_capital)}</Typography>
                </Grid>
                <Grid item xs={3}>
                  <Typography variant="subtitle2">Total Risk</Typography>
                  <Typography variant="h6">{formatPercent(selectedPlan.risk_management.total_risk_pct)}</Typography>
                </Grid>
                <Grid item xs={3}>
                  <Typography variant="subtitle2">Positions</Typography>
                  <Typography variant="h6">{selectedPlan.positions.length}</Typography>
                </Grid>
              </Grid>

              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Symbol</TableCell>
                      <TableCell>Entry</TableCell>
                      <TableCell>Shares</TableCell>
                      <TableCell>Value</TableCell>
                      <TableCell>Stop Loss</TableCell>
                      <TableCell>Risk</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {selectedPlan.positions.map((pos) => (
                      <TableRow key={pos.symbol}>
                        <TableCell>{pos.symbol}</TableCell>
                        <TableCell>{formatCurrency(pos.suggested_entry)}</TableCell>
                        <TableCell>{pos.shares}</TableCell>
                        <TableCell>{formatCurrency(pos.position_value)}</TableCell>
                        <TableCell>{formatCurrency(pos.stop_loss)}</TableCell>
                        <TableCell>{formatPercent(pos.risk_pct)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewPlanDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PlanBuilder;