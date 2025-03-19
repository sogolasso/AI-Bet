#!/usr/bin/env python3
"""
Script for monitoring canary deployment performance and checking metrics.
"""

import argparse
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import pandas as pd
from prometheus_client import start_http_server, Gauge
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
CANARY_ACCURACY = Gauge('canary_prediction_accuracy', 'Prediction accuracy of canary model')
CANARY_ROI = Gauge('canary_roi', 'ROI of canary model predictions')
CANARY_LATENCY = Gauge('canary_prediction_latency', 'Prediction latency of canary model')
CANARY_ERROR_RATE = Gauge('canary_error_rate', 'Error rate of canary model')

class CanaryMonitor:
    def __init__(self, prometheus_url: str, duration: int):
        self.prometheus_url = prometheus_url
        self.duration = duration
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(seconds=duration)
        
    def fetch_metrics(self) -> Dict[str, float]:
        """Fetch metrics from Prometheus."""
        try:
            # Query prediction accuracy
            accuracy_query = 'avg(betting_prediction_accuracy{environment="canary"}[5m])'
            accuracy = self._query_prometheus(accuracy_query)
            
            # Query ROI
            roi_query = 'avg(betting_roi{environment="canary"}[5m])'
            roi = self._query_prometheus(roi_query)
            
            # Query latency
            latency_query = 'avg(rate(http_request_duration_seconds_sum{environment="canary"}[5m])) / avg(rate(http_request_duration_seconds_count{environment="canary"}[5m]))'
            latency = self._query_prometheus(latency_query)
            
            # Query error rate
            error_query = 'sum(rate(http_requests_total{status=~"5..",environment="canary"}[5m])) / sum(rate(http_requests_total{environment="canary"}[5m]))'
            error_rate = self._query_prometheus(error_query)
            
            return {
                'accuracy': accuracy,
                'roi': roi,
                'latency': latency,
                'error_rate': error_rate
            }
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            return {}
            
    def _query_prometheus(self, query: str) -> float:
        """Execute a Prometheus query and return the result."""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={'query': query}
            )
            response.raise_for_status()
            result = response.json()
            
            if result['status'] == 'success' and result['data']['result']:
                return float(result['data']['result'][0]['value'][1])
            return 0.0
        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return 0.0
            
    def check_performance(self, metrics: Dict[str, float]) -> bool:
        """Check if canary performance meets requirements."""
        # Define thresholds
        thresholds = {
            'accuracy': 0.65,  # Minimum 65% accuracy
            'roi': 0.05,      # Minimum 5% ROI
            'latency': 0.5,   # Maximum 500ms latency
            'error_rate': 0.01  # Maximum 1% error rate
        }
        
        # Check each metric against thresholds
        for metric, value in metrics.items():
            if metric in thresholds:
                if metric in ['latency', 'error_rate']:
                    if value > thresholds[metric]:
                        logger.warning(f"{metric} exceeds threshold: {value} > {thresholds[metric]}")
                        return False
                else:
                    if value < thresholds[metric]:
                        logger.warning(f"{metric} below threshold: {value} < {thresholds[metric]}")
                        return False
                        
        return True
        
    def monitor(self):
        """Main monitoring loop."""
        logger.info(f"Starting canary monitoring for {self.duration} seconds")
        
        # Start Prometheus metrics server
        start_http_server(8000)
        
        metrics_history = []
        while datetime.now() < self.end_time:
            # Fetch current metrics
            metrics = self.fetch_metrics()
            
            # Update Prometheus metrics
            CANARY_ACCURACY.set(metrics.get('accuracy', 0))
            CANARY_ROI.set(metrics.get('roi', 0))
            CANARY_LATENCY.set(metrics.get('latency', 0))
            CANARY_ERROR_RATE.set(metrics.get('error_rate', 0))
            
            # Store metrics in history
            metrics_history.append({
                'timestamp': datetime.now(),
                **metrics
            })
            
            # Check performance
            if not self.check_performance(metrics):
                logger.error("Canary deployment failed performance check")
                return False
                
            # Log current metrics
            logger.info(f"Current metrics: {metrics}")
            
            # Wait before next check
            time.sleep(60)  # Check every minute
            
        # Analyze metrics history
        df = pd.DataFrame(metrics_history)
        self._analyze_metrics(df)
        
        return True
        
    def _analyze_metrics(self, df: pd.DataFrame):
        """Analyze metrics history for trends and anomalies."""
        # Calculate statistics
        stats = df.describe()
        logger.info(f"Metrics statistics:\n{stats}")
        
        # Check for trends
        for metric in ['accuracy', 'roi', 'latency', 'error_rate']:
            if metric in df.columns:
                trend = np.polyfit(range(len(df)), df[metric], 1)[0]
                logger.info(f"{metric} trend: {trend}")
                
                # Alert on negative trends
                if trend < 0 and metric in ['accuracy', 'roi']:
                    logger.warning(f"Negative trend detected for {metric}")
                elif trend > 0 and metric in ['latency', 'error_rate']:
                    logger.warning(f"Positive trend detected for {metric}")

def main():
    parser = argparse.ArgumentParser(description='Monitor canary deployment performance')
    parser.add_argument('--prometheus-url', default='http://localhost:9090',
                      help='URL of Prometheus server')
    parser.add_argument('--duration', type=int, default=3600,
                      help='Duration to monitor in seconds')
    
    args = parser.parse_args()
    
    monitor = CanaryMonitor(args.prometheus_url, args.duration)
    success = monitor.monitor()
    
    if success:
        logger.info("Canary deployment monitoring completed successfully")
        exit(0)
    else:
        logger.error("Canary deployment monitoring failed")
        exit(1)

if __name__ == '__main__':
    main() 