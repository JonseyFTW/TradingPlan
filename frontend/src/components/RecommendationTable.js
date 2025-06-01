import React from 'react';
import {
  Table, TableBody, TableCell, TableHead, TableRow, Button, TableContainer, Paper
} from '@mui/material';

export default function RecommendationTable({ recs, onSelect }) {
  return (
    <TableContainer component={Paper} sx={{ mt: 4, overflowX: 'auto' }}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Symbol</TableCell>
          <TableCell>Score</TableCell>
          <TableCell>Price</TableCell>
          <TableCell>Action</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {(recs || []).map(r=>(
          <TableRow key={r.symbol}>
            <TableCell>{r.symbol}</TableCell>
            <TableCell>{r.score}</TableCell>
            <TableCell>${r.price}</TableCell>
            <TableCell>
              <Button onClick={()=>onSelect(r.symbol)}>View</Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
