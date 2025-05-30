import React from 'react';
import RecommendationTable from './RecommendationTable';

export default function AlertsList({ recs, onSelect }) {
  return <RecommendationTable recs={recs} onSelect={onSelect}/>;
}
