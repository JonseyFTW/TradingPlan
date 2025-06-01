import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Chip,
  IconButton,
  Alert
} from '@mui/material';
import { Add, Edit, Delete, TrendingUp, TrendingDown } from '@mui/icons-material';

const Portfolio = () => {
  const [positions, setPositions] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPosition, setEditingPosition] = useState(null);
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    symbol: '',
    entry_date: new Date().toISOString().split('T')[0],
    entry_price: '',
    quantity: '',
    stop_loss: '',
    take_profit: '',
    notes: ''
  });

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  const fetchPortfolioData = async () => {
    try {
      const [positionsRes, performanceRes] = await Promise.all([
        axios.get('/api/portfolio/positions'),
        axios.get('/api/portfolio/performance')
      ]);

      setPositions(positionsRes.data.positions || []);
      setPerformance(performanceRes.data.portfolio_performance || null);
    } catch (err) {
      setError('Failed to load portfolio data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFormSubmit = async () => {
    try {
      if (editingPosition) {
        await axios.put(`/api/portfolio/positions/${editingPosition.id}`, formData);
      } else {
        await axios.post('/api/portfolio/positions', formData);
      }

      setDialogOpen(false);
      setEditingPosition(null);
      setFormData({
        symbol: '',
        entry_date: new Date().toISOString().split('T')[0],
        entry_price: '',
        quantity: '',
        stop_loss: '',
        take_profit: '',
        notes: ''
      });
      
      fetchPortfolioData();
    } catch (err) {
      setError('Failed to save position: ' + err.message);
    }
  };

  const handleEditPosition = (position) => {
    setEditingPosition(position);
    setFormData({
      symbol: position.symbol,
      entry_date: position.entry_date,
      entry_price: position.entry_price,
      quantity: position.quantity,
      stop_loss: position.stop_loss || '',
      take_profit: position.take_profit || '',
      notes: position.notes || ''
    });
    setDialogOpen(true);
  };

  const handleDeletePosition = async (positionId) => {
    if (!window.confirm('Are you sure you want to delete this position?')) return;

    try {
      await axios.delete(`/api/portfolio/positions/${positionId}`);
      fetchPortfolioData();
    } catch (err) {
      setError('Failed to delete position: ' + err.message);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'OPEN': return 'primary';
      case 'CLOSED': return 'success';
      case 'STOPPED_OUT': return 'error';
      default: return 'default';
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  if (loading) return <Typography>Loading portfolio...</Typography>;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Portfolio Tracker</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setDialogOpen(true)}
        >
          Add Position
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Portfolio Summary */}
      {performance && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="primary">
                  Total Value
                </Typography>
                <Typography variant="h4">
                  {formatCurrency(performance.total_current_value)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Cost Basis: {formatCurrency(performance.total_cost_basis)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="primary">
                  Total P&L
                </Typography>
                <Typography 
                  variant="h4"
                  color={performance.total_pnl >= 0 ? 'success.main' : 'error.main'}
                >
                  {formatCurrency(performance.total_pnl)}
                </Typography>
                <Typography 
                  variant="body2"
                  color={performance.total_return_pct >= 0 ? 'success.main' : 'error.main'}
                >
                  {performance.total_return_pct >= 0 ? '+' : ''}{performance.total_return_pct}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="primary">
                  Open Positions
                </Typography>
                <Typography variant="h4">
                  {performance.open_positions}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total: {performance.total_positions}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="primary">
                  Realized P&L
                </Typography>
                <Typography 
                  variant="h4"
                  color={performance.total_realized_pnl >= 0 ? 'success.main' : 'error.main'}
                >
                  {formatCurrency(performance.total_realized_pnl)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  From {performance.closed_positions} trades
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Positions Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Current Positions
          </Typography>
          
          <TableContainer component={Paper} sx={{ overflowX: 'auto', maxWidth: '100%' }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Entry Date</TableCell>
                  <TableCell align="right">Entry Price</TableCell>
                  <TableCell align="right">Current Price</TableCell>
                  <TableCell align="right">Quantity</TableCell>
                  <TableCell align="right">Position Value</TableCell>
                  <TableCell align="right">P&L</TableCell>
                  <TableCell align="right">P&L %</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {positions.map((position) => (
                  <TableRow key={position.id}>
                    <TableCell>
                      <Typography variant="body2" fontWeight="bold">
                        {position.symbol}
                      </Typography>
                    </TableCell>
                    <TableCell>{position.entry_date}</TableCell>
                    <TableCell align="right">{formatCurrency(position.entry_price)}</TableCell>
                    <TableCell align="right">{formatCurrency(position.current_price)}</TableCell>
                    <TableCell align="right">{position.quantity}</TableCell>
                    <TableCell align="right">{formatCurrency(position.position_value)}</TableCell>
                    <TableCell align="right">
                      <Typography 
                        color={position.unrealized_pnl >= 0 ? 'success.main' : 'error.main'}
                        sx={{ display: 'flex', alignItems: 'center' }}
                      >
                        {position.unrealized_pnl >= 0 ? <TrendingUp /> : <TrendingDown />}
                        {formatCurrency(position.unrealized_pnl)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography 
                        color={position.unrealized_pnl_pct >= 0 ? 'success.main' : 'error.main'}
                      >
                        {position.unrealized_pnl_pct >= 0 ? '+' : ''}{position.unrealized_pnl_pct}%
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip 
                        label={position.status} 
                        color={getStatusColor(position.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <IconButton 
                        size="small" 
                        onClick={() => handleEditPosition(position)}
                      >
                        <Edit />
                      </IconButton>
                      <IconButton 
                        size="small" 
                        onClick={() => handleDeletePosition(position.id)}
                      >
                        <Delete />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Add/Edit Position Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingPosition ? 'Edit Position' : 'Add New Position'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Symbol"
                value={formData.symbol}
                onChange={(e) => setFormData({...formData, symbol: e.target.value.toUpperCase()})}
                fullWidth
                disabled={editingPosition !== null}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Entry Date"
                type="date"
                value={formData.entry_date}
                onChange={(e) => setFormData({...formData, entry_date: e.target.value})}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Entry Price"
                type="number"
                value={formData.entry_price}
                onChange={(e) => setFormData({...formData, entry_price: e.target.value})}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Quantity"
                type="number"
                value={formData.quantity}
                onChange={(e) => setFormData({...formData, quantity: e.target.value})}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Stop Loss"
                type="number"
                value={formData.stop_loss}
                onChange={(e) => setFormData({...formData, stop_loss: e.target.value})}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Take Profit"
                type="number"
                value={formData.take_profit}
                onChange={(e) => setFormData({...formData, take_profit: e.target.value})}
                fullWidth
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Notes"
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                fullWidth
                multiline
                rows={2}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleFormSubmit} variant="contained">
            {editingPosition ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Portfolio;