import React from 'react';
import { List, ListItem, IconButton, Typography } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';

export default function Watchlist({ items, onRemove }) {
  return (
    <List sx={{ mt:4 }}>
      {items.map(sym=>(
        <ListItem
          key={sym}
          secondaryAction={
            <IconButton edge="end" onClick={()=>onRemove(sym)}>
              <DeleteIcon/>
            </IconButton>
          }
        >
          <Typography>{sym}</Typography>
        </ListItem>
      ))}
    </List>
  );
}
