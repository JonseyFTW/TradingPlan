import React from 'react';
import { Card, CardContent, Typography, Grid, Box, Chip, Alert, Divider } from '@mui/material';

export default function ReportCard({ report }) {
  if (!report || !report.indicators || !report.fib_levels || !report.plan) {
    return <div>Loading report...</div>;
  }
  
  const { symbol, price, fib_levels, indicators, plan, score, analysis } = report;
  
  const getConvictionColor = (conviction) => {
    switch(conviction) {
      case 'HIGH': return 'success';
      case 'MODERATE': return 'warning';
      case 'LOW': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ mt: 4 }}>
      {/* Header */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap">
            <Typography variant="h4">{symbol} @ ${price}</Typography>
            <Box display="flex" gap={1} alignItems="center">
              <Chip label={`Score: ${score?.toFixed(1) || '0.0'}`} color="primary" />
              {analysis?.summary && (
                <Chip 
                  label={`${analysis.summary.conviction} CONVICTION`} 
                  color={getConvictionColor(analysis.summary.conviction)}
                />
              )}
            </Box>
          </Box>
          {analysis?.summary && (
            <Alert severity={getConvictionColor(analysis.summary.conviction)} sx={{ mt: 2 }}>
              <Typography variant="body2">{analysis.summary.recommendation}</Typography>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Technical Analysis */}
      {analysis && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>📈 Technical Analysis</Typography>
            
            <Grid container spacing={3}>
              {/* RSI Analysis */}
              <Grid item xs={12} md={6}>
                <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold">RSI Analysis</Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>{analysis.rsi_analysis}</Typography>
                </Box>
              </Grid>

              {/* MACD Analysis */}
              <Grid item xs={12} md={6}>
                <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold">MACD Analysis</Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>{analysis.macd_analysis}</Typography>
                </Box>
              </Grid>

              {/* ADX Analysis */}
              <Grid item xs={12} md={6}>
                <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold">Trend Strength (ADX)</Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>{analysis.adx_analysis}</Typography>
                </Box>
              </Grid>

              {/* Bollinger Bands */}
              <Grid item xs={12} md={6}>
                <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold">Bollinger Bands</Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>{analysis.bollinger_analysis}</Typography>
                </Box>
              </Grid>

              {/* Fibonacci Analysis */}
              <Grid item xs={12}>
                <Box sx={{ p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold">🔀 Fibonacci Analysis</Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>{analysis.fibonacci_analysis}</Typography>
                </Box>
              </Grid>

              {/* Volume Analysis */}
              <Grid item xs={12} md={6}>
                <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="subtitle1" fontWeight="bold">📊 Volume Analysis</Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>{analysis.volume_analysis}</Typography>
                </Box>
              </Grid>

              {/* Relative Strength Analysis */}
              {analysis.relative_strength && !analysis.relative_strength.error && (
                <Grid item xs={12} md={6}>
                  <Box sx={{ p: 2, bgcolor: 'success.light', borderRadius: 1 }}>
                    <Typography variant="subtitle1" fontWeight="bold">📈 Relative Strength</Typography>
                    <Typography variant="body2" sx={{ mt: 1, mb: 2 }}>
                      {analysis.relative_strength.interpretation}
                    </Typography>
                    
                    <Grid container spacing={1}>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="caption" color="text.secondary">
                          vs SPY (20d)
                        </Typography>
                        <Typography 
                          variant="body2" 
                          color={analysis.relative_strength.vs_spy?.outperforming_market_20d ? 'success.main' : 'error.main'}
                          fontWeight="bold"
                        >
                          {analysis.relative_strength.vs_spy?.relative_strength_20d > 0 ? '+' : ''}
                          {analysis.relative_strength.vs_spy?.relative_strength_20d}%
                        </Typography>
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="caption" color="text.secondary">
                          Beta
                        </Typography>
                        <Typography variant="body2" fontWeight="bold">
                          {analysis.relative_strength.vs_spy?.beta}
                        </Typography>
                      </Grid>
                      
                      {analysis.relative_strength.vs_sector && !analysis.relative_strength.vs_sector.error && (
                        <Grid item xs={12}>
                          <Typography variant="caption" color="text.secondary">
                            vs {analysis.relative_strength.vs_sector.sector_etf} (20d)
                          </Typography>
                          <Typography 
                            variant="body2" 
                            color={analysis.relative_strength.vs_sector.outperforming_sector ? 'success.main' : 'error.main'}
                            fontWeight="bold"
                          >
                            {analysis.relative_strength.vs_sector.relative_strength_vs_sector > 0 ? '+' : ''}
                            {analysis.relative_strength.vs_sector.relative_strength_vs_sector}%
                          </Typography>
                        </Grid>
                      )}
                    </Grid>
                  </Box>
                </Grid>
              )}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Risk Factors */}
      {analysis?.risk_factors && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h5" gutterBottom>⚠️ Risk Factors</Typography>
            {analysis.risk_factors.map((risk, index) => (
              <Alert key={index} severity="warning" sx={{ mb: 1 }}>
                <Typography variant="body2">{risk}</Typography>
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Trading Plan & Levels */}
      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom>🎯 Trading Plan & Key Levels</Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Typography variant="h6" color="primary">Fibonacci Levels</Typography>
              {Object.entries(fib_levels).map(([k,v])=>
                <Typography key={k} variant="body2">{k}: ${v}</Typography>
              )}
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Typography variant="h6" color="primary">Entry & Exit Plan</Typography>
              <Typography variant="body2">Entry Zone: ${plan.entry?.[0]} – ${plan.entry?.[1]}</Typography>
              <Typography variant="body2">Stop Loss: ${plan.stop_loss}</Typography>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle2">Targets:</Typography>
              {(plan.targets || []).map((t,i)=>
                <Typography key={i} variant="body2">
                  Target {i+1}: ${t.price} ({t.pct}% position)
                </Typography>
              )}
            </Grid>

            <Grid item xs={12} md={4}>
              <Typography variant="h6" color="primary">Key Indicators</Typography>
              <Typography variant="body2">RSI: {indicators.RSI !== null ? indicators.RSI?.toFixed(2) : 'N/A'}</Typography>
              <Typography variant="body2">MACD: {indicators.MACD !== null ? indicators.MACD?.toFixed(4) : 'N/A'}</Typography>
              <Typography variant="body2">ADX: {indicators.ADX !== null ? indicators.ADX?.toFixed(2) : 'N/A'}</Typography>
              <Typography variant="body2">ATR: {indicators.ATR !== null ? indicators.ATR?.toFixed(2) : 'N/A'}</Typography>
              <Typography variant="body2">Volume: {indicators.Volume?.toLocaleString()}</Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
}
