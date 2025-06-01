import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  AppBar, Toolbar, Typography, Button, Container, TextField, MenuItem, CircularProgress, Box
} from '@mui/material';
import ChartPanel from './components/ChartPanel';
import ReportCard from './components/ReportCard';
import RecommendationTable from './components/RecommendationTable';
import Watchlist from './components/Watchlist';
import AlertsList from './components/AlertsList';
import StockScreener from './components/StockScreener';
import MarketDashboard from './components/MarketDashboard';
import Portfolio from './components/Portfolio';
import PlanBuilder from './components/PlanBuilder';

function App() {
  const [view, setView] = useState('analyze');
  const [symbol, setSymbol] = useState('');
  const [report, setReport] = useState(null);
  const [indices, setIndices] = useState([]);
  const [recs, setRecs] = useState([]);
  const [watch, setWatch] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);

  const analyze = useCallback(async(sym)=>{
    setLoading(true);
    try {
      const { data } = await axios.get(`/api/analyze/${sym}`);
      setReport(data);
      setView('analyze');
    } catch (error) {
      alert("Not found"); setReport(null);
    }
    setLoading(false);
  }, []);

  useEffect(()=>{
    // load indices
    axios.get('/api/indices').then(r=>setIndices(r.data.available || [])).catch(e=>setIndices([]));
    // load watchlist
    axios.get('/api/watchlist').then(r=>setWatch(r.data.watchlist || [])).catch(e=>setWatch([]));
    
    // Check for symbol parameter in URL and auto-analyze
    const urlParams = new URLSearchParams(window.location.search);
    const symbolParam = urlParams.get('symbol');
    if (symbolParam) {
      setSymbol(symbolParam.toUpperCase());
      analyze(symbolParam.toUpperCase());
    }
  },[analyze]);

  const fetchRecs = async()=>{
    setLoading(true);
    const { data } = await axios.get('/api/recommendations');
    setRecs(data.recommendations);
    setView('recs');
    setLoading(false);
  };

  const fetchAlerts = async()=>{
    setLoading(true);
    const { data } = await axios.get('/api/alerts/latest');
    setAlerts(data.recommendations);
    setView('alerts');
    setLoading(false);
  };

  const addWatch = async(sym)=>{
    await axios.post(`/api/watchlist/${sym}`);
    setWatch(ws=>[...(ws || []),sym]);
  };

  const removeWatch = async(sym)=>{
    await axios.delete(`/api/watchlist/${sym}`);
    setWatch(ws=>(ws || []).filter(w=>w!==sym));
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow:1 }}>Swing Trade Analyzer</Typography>
          {['analyze','screener','plan-builder','market','portfolio','recs','watch','alerts'].map(v=>
            <Button
              key={v}
              color="inherit"
              onClick={()=>{
                if(v==='recs') fetchRecs();
                else if(v==='alerts') fetchAlerts();
                setView(v);
              }}
            >
              {v.toUpperCase()}
            </Button>
          )}
        </Toolbar>
      </AppBar>
      <Container sx={{ py:4 }}>
        {view==='analyze' && (
          <>
            <Box sx={{ display:'flex', gap:2, mb:2 }}>
              <TextField
                label="Ticker"
                value={symbol}
                onChange={e=>setSymbol(e.target.value.toUpperCase())}
              />
              <Button variant="contained" onClick={()=>analyze(symbol)}>Analyze</Button>
              <TextField
                select
                label="Scan Index"
                value={symbol}
                onChange={e=>analyze(e.target.value)}
                sx={{ width:160 }}
              >
                {(indices || []).map(i=>
                  <MenuItem key={i} value={i}>{i.toUpperCase()}</MenuItem>
                )}
              </TextField>
              {report && !(watch || []).includes(report.symbol) && (
                <Button onClick={()=>addWatch(report.symbol)}>+Watch</Button>
              )}
            </Box>
            {loading && <CircularProgress/>}
            {report && (
              <>
                <ChartPanel ts={report.timeseries} fibs={report.fib_levels}/>
                <ReportCard report={report}/>
              </>
            )}
          </>
        )}

        {view==='recs' && (
          <>
            {loading ? <CircularProgress/> :
              <RecommendationTable
                recs={recs}
                onSelect={sym=>analyze(sym)}
              />
            }
          </>
        )}

        {view==='watch' && (
          <Watchlist items={watch} onRemove={removeWatch}/>
        )}

        {view==='screener' && <StockScreener />}

        {view==='market' && <MarketDashboard />}

        {view==='portfolio' && <Portfolio />}

        {view==='plan-builder' && <PlanBuilder />}

        {view==='alerts' && (
          <>
            {loading ? <CircularProgress/> :
              <AlertsList recs={alerts} onSelect={sym=>analyze(sym)}/>
            }
          </>
        )}
      </Container>
    </>
  );
}

export default App;
