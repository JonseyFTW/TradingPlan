import React from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import 'chartjs-adapter-date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function ChartPanel({ ts, fibs }) {
  if (!ts || !ts.dates || !ts.closes || !fibs) {
    return <div>Loading chart...</div>;
  }
  
  const dates = ts.dates, closes = ts.closes;
  const datasets = [
    { 
      label: 'Close Price', 
      data: dates.map((d,i) => ({x:d, y:closes[i]})), 
      borderColor: 'rgb(75, 192, 192)',
      backgroundColor: 'rgba(75, 192, 192, 0.2)',
      tension: 0.3,
      fill: false
    },
    ...Object.entries(fibs).map(([lab, price], index) => ({
      label: `Fib ${lab}`,
      data: dates.map(d => ({x:d, y:price})),
      borderColor: `hsl(${index * 60}, 70%, 50%)`,
      borderDash: [5, 5],
      tension: 0,
      fill: false,
      pointRadius: 0
    }))
  ];
  return (
    <Line
      options={{
        responsive: true,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          x: { 
            type: 'time',
            display: true,
            title: {
              display: true,
              text: 'Date'
            }
          },
          y: { 
            display: true,
            title: {
              display: true,
              text: 'Price ($)'
            }
          }
        },
        plugins: {
          legend: {
            position: 'bottom'
          },
          tooltip: {
            mode: 'index',
            intersect: false,
          }
        }
      }}
      data={{ datasets }}
    />
  );
}
