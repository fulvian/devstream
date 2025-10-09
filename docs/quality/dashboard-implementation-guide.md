# Dashboard Implementation Guide

**Purpose**: Technical implementation guide for developers building the DevStream Quality Monitoring Dashboard

## 🏗️ Project Structure

```
dashboard/
├── frontend/                 # React TypeScript application
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   │   ├── charts/     # Chart components (Chart.js/D3)
│   │   │   ├── alerts/     # Alert management components
│   │   │   ├── metrics/    # Metrics display components
│   │   │   └── common/     # Shared components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── services/       # API and WebSocket services
│   │   ├── types/          # TypeScript type definitions
│   │   ├── utils/          # Utility functions
│   │   └── styles/         # Global styles and themes
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── backend/                 # Node.js TypeScript backend
│   ├── src/
│   │   ├── routes/         # REST API routes
│   │   ├── websocket/      # WebSocket handlers
│   │   ├── services/       # Business logic services
│   │   ├── models/         # Data models
│   │   ├── middleware/     # Express middleware
│   │   ├── config/         # Configuration management
│   │   └── utils/          # Utility functions
│   ├── tests/              # Unit and integration tests
│   ├── package.json
│   └── tsconfig.json
└── deployment/              # Docker and deployment configs
    ├── docker-compose.yml
    ├── Dockerfile.frontend
    ├── Dockerfile.backend
    └── nginx.conf
```

## 🔧 Technology Stack

### Frontend Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.0.0",
    "chart.js": "^4.4.0",
    "react-chartjs-2": "^5.2.0",
    "socket.io-client": "^4.7.0",
    "axios": "^1.6.0",
    "react-query": "^3.39.0",
    "date-fns": "^2.30.0",
    "react-router-dom": "^6.8.0",
    "@mui/material": "^5.14.0",
    "@mui/icons-material": "^5.14.0",
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "vite": "^4.4.0",
    "eslint": "^8.45.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "prettier": "^3.0.0"
  }
}
```

### Backend Dependencies

```json
{
  "dependencies": {
    "express": "^4.18.0",
    "socket.io": "^4.7.0",
    "typescript": "^5.0.0",
    "prom-client": "^14.2.0",
    "ws": "^8.14.0",
    "node-cron": "^3.0.0",
    "jsonwebtoken": "^9.0.0",
    "bcryptjs": "^2.4.0",
    "helmet": "^7.0.0",
    "cors": "^2.8.0",
    "compression": "^1.7.0",
    "express-rate-limit": "^6.10.0",
    "winston": "^3.10.0",
    "joi": "^17.9.0",
    "redis": "^4.6.0",
    "pg": "^8.11.0"
  },
  "devDependencies": {
    "@types/express": "^4.17.0",
    "@types/node": "^20.5.0",
    "@types/ws": "^8.5.0",
    "@types/jsonwebtoken": "^9.0.0",
    "@types/bcryptjs": "^2.4.0",
    "@types/cors": "^2.8.0",
    "@types/compression": "^1.7.0",
    "@types/pg": "^8.10.0",
    "nodemon": "^3.0.0",
    "ts-node": "^10.9.0",
    "jest": "^29.6.0",
    "@types/jest": "^29.5.0",
    "supertest": "^6.3.0",
    "@types/supertest": "^2.0.0"
  }
}
```

## 🎨 Frontend Implementation

### 1. Core Types Definition

```typescript
// src/types/dashboard.ts
export interface MetricData {
  timestamp: number;
  value: number;
  labels?: Record<string, string>;
}

export interface TimeSeriesData {
  metric: string;
  dataPoints: MetricData[];
  aggregation?: 'avg' | 'sum' | 'min' | 'max';
}

export interface AlertDefinition {
  id: string;
  name: string;
  description: string;
  metric: string;
  threshold: number;
  operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte';
  severity: 'info' | 'warning' | 'critical';
  enabled: boolean;
  cooldownPeriod: number;
  notifications: NotificationConfig[];
}

export interface NotificationConfig {
  type: 'email' | 'slack' | 'webhook';
  target: string;
  template?: string;
}

export interface AlertInstance {
  id: string;
  ruleId: string;
  status: 'active' | 'resolved' | 'acknowledged';
  triggeredAt: number;
  resolvedAt?: number;
  acknowledgedAt?: number;
  currentValue: number;
  severity: string;
  message: string;
}

export interface DashboardConfig {
  refreshInterval: number;
  autoRefresh: boolean;
  theme: 'light' | 'dark';
  defaultTimeRange: TimeRange;
  visibleMetrics: string[];
}

export type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d';
```

### 2. WebSocket Service Implementation

```typescript
// src/services/websocket.ts
import { io, Socket } from 'socket.io-client';
import { MetricData, AlertInstance } from '../types/dashboard';

export class WebSocketService {
  private socket: Socket | null = null;
  private subscribers: Map<string, Set<(data: any) => void>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.socket = io(url, {
        transports: ['websocket'],
        upgrade: false,
        rememberUpgrade: false,
      });

      this.socket.on('connect', () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        resolve();
      });

      this.socket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason);
        this.handleReconnect();
      });

      this.socket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
        reject(error);
      });

      this.socket.on('metric_update', (data: MetricData) => {
        this.notifySubscribers('metric_update', data);
      });

      this.socket.on('alert_update', (data: AlertInstance) => {
        this.notifySubscribers('alert_update', data);
      });
    });
  }

  subscribe(event: string, callback: (data: any) => void): () => void {
    if (!this.subscribers.has(event)) {
      this.subscribers.set(event, new Set());
    }

    this.subscribers.get(event)!.add(callback);

    // Return unsubscribe function
    return () => {
      this.subscribers.get(event)?.delete(callback);
    };
  }

  subscribeToMetrics(metrics: string[]): void {
    this.socket?.emit('subscribe_metrics', { metrics });
  }

  unsubscribeFromMetrics(metrics: string[]): void {
    this.socket?.emit('unsubscribe_metrics', { metrics });
  }

  private notifySubscribers(event: string, data: any): void {
    const subscribers = this.subscribers.get(event);
    if (subscribers) {
      subscribers.forEach(callback => callback(data));
    }
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.socket?.connect();
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
    }
  }

  disconnect(): void {
    this.socket?.disconnect();
    this.socket = null;
    this.subscribers.clear();
  }
}
```

### 3. Metrics Hook Implementation

```typescript
// src/hooks/useMetrics.ts
import { useState, useEffect, useCallback } from 'react';
import { WebSocketService } from '../services/websocket';
import { MetricData, TimeRange } from '../types/dashboard';

export const useMetrics = (metrics: string[], timeRange: TimeRange) => {
  const [data, setData] = useState<Record<string, MetricData[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsService] = useState(() => new WebSocketService());

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/metrics/history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metrics, timeRange })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [metrics, timeRange]);

  useEffect(() => {
    const connectWebSocket = async () => {
      try {
        await wsService.connect(process.env.REACT_APP_WS_URL!);

        // Subscribe to real-time updates
        wsService.subscribeToMetrics(metrics);

        // Listen for real-time updates
        wsService.subscribe('metric_update', (update: MetricData) => {
          setData(prev => ({
            ...prev,
            [update.metric]: [...(prev[update.metric] || []), update]
          }));
        });
      } catch (err) {
        console.error('WebSocket connection failed:', err);
      }
    };

    connectWebSocket();

    // Fetch initial data
    fetchData();

    return () => {
      wsService.disconnect();
    };
  }, [fetchData, metrics, wsService]);

  return { data, loading, error, refetch: fetchData };
};
```

### 4. Chart Component Implementation

```typescript
// src/components/charts/MetricChart.tsx
import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { MetricData } from '../../types/dashboard';
import { formatTime, formatValue } from '../../utils/formatters';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface MetricChartProps {
  data: MetricData[];
  metric: string;
  title?: string;
  color?: string;
  height?: number;
  showGrid?: boolean;
  animationDuration?: number;
}

export const MetricChart: React.FC<MetricChartProps> = ({
  data,
  metric,
  title,
  color = '#3B82F6',
  height = 300,
  showGrid = true,
  animationDuration = 750,
}) => {
  const chartData = useMemo(() => {
    return {
      labels: data.map(point => formatTime(point.timestamp)),
      datasets: [
        {
          label: metric,
          data: data.map(point => point.value),
          borderColor: color,
          backgroundColor: `${color}20`,
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 4,
        },
      ],
    };
  }, [data, metric, color]);

  const options: ChartOptions<'line'> = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: animationDuration,
    },
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: !!title,
        text: title,
        font: {
          size: 16,
          weight: 'bold',
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: (context) => {
            return `${context.dataset.label}: ${formatValue(context.parsed.y)}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          display: showGrid,
          color: '#E5E7EB',
        },
        ticks: {
          maxTicksLimit: 8,
        },
      },
      y: {
        grid: {
          display: showGrid,
          color: '#E5E7EB',
        },
        ticks: {
          callback: (value) => formatValue(value as number),
        },
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
  }), [title, showGrid, animationDuration]);

  return (
    <div style={{ height }}>
      <Line data={chartData} options={options} />
    </div>
  );
};
```

### 5. Alert Management Component

```typescript
// src/components/alerts/AlertPanel.tsx
import React, { useState } from 'react';
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Close as CloseIcon,
  Notifications as NotificationsIcon,
} from '@mui/icons-material';
import { AlertInstance } from '../../types/dashboard';
import { useAlerts } from '../../hooks/useAlerts';
import { formatRelativeTime } from '../../utils/formatters';

const severityConfig = {
  info: { color: 'info', icon: InfoIcon },
  warning: { color: 'warning', icon: WarningIcon },
  critical: { color: 'error', icon: ErrorIcon },
};

export const AlertPanel: React.FC = () => {
  const { alerts, acknowledgeAlert, resolveAlert } = useAlerts();
  const [selectedAlert, setSelectedAlert] = useState<AlertInstance | null>(null);

  const activeAlerts = alerts.filter(alert => alert.status === 'active');
  const acknowledgedAlerts = alerts.filter(alert => alert.status === 'acknowledged');

  const handleAcknowledge = async (alertId: string) => {
    await acknowledgeAlert(alertId);
  };

  const handleResolve = async (alertId: string) => {
    await resolveAlert(alertId);
  };

  return (
    <Box>
      {/* Active Alerts */}
      {activeAlerts.length > 0 && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <AlertTitle>
            <Box display="flex" alignItems="center" gap={1}>
              <NotificationsIcon />
              {activeAlerts.length} Active Alert{activeAlerts.length > 1 ? 's' : ''}
            </Box>
          </AlertTitle>
          <List dense>
            {activeAlerts.map((alert) => (
              <AlertItem
                key={alert.id}
                alert={alert}
                onAcknowledge={() => handleAcknowledge(alert.id)}
                onResolve={() => handleResolve(alert.id)}
                onClick={() => setSelectedAlert(alert)}
              />
            ))}
          </List>
        </Alert>
      )}

      {/* Acknowledged Alerts */}
      {acknowledgedAlerts.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <AlertTitle>
            {acknowledgedAlerts.length} Acknowledged Alert{acknowledgedAlerts.length > 1 ? 's' : ''}
          </AlertTitle>
          <List dense>
            {acknowledgedAlerts.map((alert) => (
              <AlertItem
                key={alert.id}
                alert={alert}
                onResolve={() => handleResolve(alert.id)}
                onClick={() => setSelectedAlert(alert)}
              />
            ))}
          </List>
        </Alert>
      )}

      {/* Alert Details Dialog */}
      <Dialog
        open={!!selectedAlert}
        onClose={() => setSelectedAlert(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedAlert && (
          <>
            <DialogTitle>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box display="flex" alignItems="center" gap={1}>
                  {React.createElement(severityConfig[selectedAlert.severity as keyof typeof severityConfig].icon)}
                  {selectedAlert.severity.toUpperCase()} Alert
                </Box>
                <IconButton onClick={() => setSelectedAlert(null)}>
                  <CloseIcon />
                </IconButton>
              </Box>
            </DialogTitle>
            <DialogContent>
              <Typography variant="body1" gutterBottom>
                {selectedAlert.message}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Current Value: {selectedAlert.currentValue}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Triggered: {formatRelativeTime(selectedAlert.triggeredAt)}
              </Typography>
            </DialogContent>
            <DialogActions>
              {selectedAlert.status === 'active' && (
                <Button
                  onClick={() => handleAcknowledge(selectedAlert.id)}
                  variant="outlined"
                >
                  Acknowledge
                </Button>
              )}
              <Button
                onClick={() => handleResolve(selectedAlert.id)}
                variant="contained"
                color="primary"
              >
                Resolve
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

interface AlertItemProps {
  alert: AlertInstance;
  onAcknowledge?: () => void;
  onResolve?: () => void;
  onClick: () => void;
}

const AlertItem: React.FC<AlertItemProps> = ({
  alert,
  onAcknowledge,
  onResolve,
  onClick,
}) => {
  const SeverityIcon = severityConfig[alert.severity as keyof typeof severityConfig].icon;

  return (
    <ListItem
      onClick={onClick}
      sx={{
        cursor: 'pointer',
        '&:hover': {
          backgroundColor: 'action.hover',
        },
      }}
    >
      <SeverityIcon color={severityConfig[alert.severity as keyof typeof severityConfig].color as any} />
      <ListItemText
        primary={alert.message}
        secondary={formatRelativeTime(alert.triggeredAt)}
      />
      <Box display="flex" gap={1}>
        {onAcknowledge && alert.status === 'active' && (
          <Button size="small" onClick={(e) => {
            e.stopPropagation();
            onAcknowledge();
          }}>
            Acknowledge
          </Button>
        )}
        {onResolve && (
          <Button size="small" variant="contained" onClick={(e) => {
            e.stopPropagation();
            onResolve();
          }}>
            Resolve
          </Button>
        )}
      </Box>
    </ListItem>
  );
};
```

## 🔙 Backend Implementation

### 1. WebSocket Server Implementation

```typescript
// backend/src/websocket/websocketServer.ts
import { Server as SocketIOServer } from 'socket.io';
import { Server as HTTPServer } from 'http';
import { authenticateSocket } from '../middleware/auth';
import { MetricsService } from '../services/metricsService';
import { AlertService } from '../services/alertService';

export class WebSocketServer {
  private io: SocketIOServer;
  private metricsService: MetricsService;
  private alertService: AlertService;
  private subscriptions: Map<string, Set<string>> = new Map();

  constructor(httpServer: HTTPServer) {
    this.io = new SocketIOServer(httpServer, {
      cors: {
        origin: process.env.FRONTEND_URL || "http://localhost:3000",
        methods: ["GET", "POST"]
      },
      transports: ['websocket', 'polling']
    });

    this.metricsService = new MetricsService();
    this.alertService = new AlertService();

    this.setupMiddleware();
    this.setupEventHandlers();
    this.startMetricsBroadcast();
  }

  private setupMiddleware(): void {
    this.io.use(authenticateSocket);
  }

  private setupEventHandlers(): void {
    this.io.on('connection', (socket) => {
      console.log(`Client connected: ${socket.id}`);

      socket.on('subscribe_metrics', async (data: { metrics: string[] }) => {
        await this.handleMetricSubscription(socket, data.metrics);
      });

      socket.on('unsubscribe_metrics', (data: { metrics: string[] }) => {
        this.handleMetricUnsubscription(socket, data.metrics);
      });

      socket.on('disconnect', () => {
        console.log(`Client disconnected: ${socket.id}`);
        this.cleanupSubscriptions(socket.id);
      });
    });
  }

  private async handleMetricSubscription(socket: any, metrics: string[]): Promise<void {
    for (const metric of metrics) {
      if (!this.subscriptions.has(metric)) {
        this.subscriptions.set(metric, new Set());
      }
      this.subscriptions.get(metric)!.add(socket.id);
    }

    // Send initial data for subscribed metrics
    const initialData = await this.metricsService.getLatestMetrics(metrics);
    socket.emit('initial_metrics', initialData);
  }

  private handleMetricUnsubscription(socket: any, metrics: string[]): void {
    for (const metric of metrics) {
      this.subscriptions.get(metric)?.delete(socket.id);
    }
  }

  private cleanupSubscriptions(socketId: string): void {
    for (const [metric, subscribers] of this.subscriptions) {
      subscribers.delete(socketId);
      if (subscribers.size === 0) {
        this.subscriptions.delete(metric);
      }
    }
  }

  private startMetricsBroadcast(): void {
    // Broadcast metrics updates every second
    setInterval(async () => {
      const activeMetrics = Array.from(this.subscriptions.keys());
      if (activeMetrics.length === 0) return;

      const metricsData = await this.metricsService.getLatestMetrics(activeMetrics);

      for (const [metric, data] of Object.entries(metricsData)) {
        const subscribers = this.subscriptions.get(metric);
        if (subscribers) {
          subscribers.forEach(socketId => {
            this.io.to(socketId).emit('metric_update', {
              metric,
              timestamp: Date.now(),
              value: data.value,
              labels: data.labels
            });
          });
        }
      }
    }, 1000);

    // Check for new alerts every 30 seconds
    setInterval(async () => {
      const newAlerts = await this.alertService.checkForNewAlerts();
      for (const alert of newAlerts) {
        this.io.emit('alert_update', alert);
      }
    }, 30000);
  }
}
```

### 2. Metrics Service Implementation

```typescript
// backend/src/services/metricsService.ts
import { promClient } from 'prom-client';
import { DatabaseService } from './databaseService';

export interface MetricValue {
  value: number;
  labels?: Record<string, string>;
  timestamp: number;
}

export class MetricsService {
  private dbService: DatabaseService;
  private metricsCache: Map<string, MetricValue> = new Map();
  private cacheExpiry = 5000; // 5 seconds

  constructor() {
    this.dbService = new DatabaseService();
  }

  async getLatestMetrics(metrics: string[]): Promise<Record<string, MetricValue>> {
    const result: Record<string, MetricValue> = {};

    for (const metric of metrics) {
      const cached = this.metricsCache.get(metric);
      if (cached && (Date.now() - cached.timestamp) < this.cacheExpiry) {
        result[metric] = cached;
      } else {
        try {
          const value = await this.fetchMetricFromPrometheus(metric);
          result[metric] = value;
          this.metricsCache.set(metric, value);
        } catch (error) {
          console.error(`Failed to fetch metric ${metric}:`, error);
          result[metric] = {
            value: 0,
            timestamp: Date.now()
          };
        }
      }
    }

    return result;
  }

  async getHistoricalMetrics(
    metrics: string[],
    startTime: number,
    endTime: number,
    resolution?: string
  ): Promise<Record<string, MetricValue[]>> {
    const result: Record<string, MetricValue[]> = {};

    for (const metric of metrics) {
      try {
        const data = await this.fetchHistoricalData(metric, startTime, endTime, resolution);
        result[metric] = data;
      } catch (error) {
        console.error(`Failed to fetch historical data for ${metric}:`, error);
        result[metric] = [];
      }
    }

    return result;
  }

  private async fetchMetricFromPrometheus(metric: string): Promise<MetricValue> {
    const prometheusUrl = process.env.PROMETHEUS_URL || 'http://localhost:9090';
    const query = encodeURIComponent(metric);

    const response = await fetch(`${prometheusUrl}/api/v1/query?query=${query}`);
    const data = await response.json();

    if (data.status === 'success' && data.data.result.length > 0) {
      const result = data.data.result[0];
      return {
        value: parseFloat(result.value[1]),
        labels: result.metric,
        timestamp: Date.now()
      };
    }

    return {
      value: 0,
      timestamp: Date.now()
    };
  }

  private async fetchHistoricalData(
    metric: string,
    startTime: number,
    endTime: number,
    resolution?: string
  ): Promise<MetricValue[]> {
    const prometheusUrl = process.env.PROMETHEUS_URL || 'http://localhost:9090';
    const query = encodeURIComponent(metric);
    const step = resolution || '1m';

    const response = await fetch(
      `${prometheusUrl}/api/v1/query_range?query=${query}&start=${startTime}&end=${endTime}&step=${step}`
    );
    const data = await response.json();

    if (data.status === 'success' && data.data.result.length > 0) {
      const result = data.data.result[0];
      return result.values.map(([timestamp, value]: [string, string]) => ({
        value: parseFloat(value),
        labels: result.metric,
        timestamp: parseInt(timestamp) * 1000 // Convert to milliseconds
      }));
    }

    return [];
  }
}
```

### 3. Alert Service Implementation

```typescript
// backend/src/services/alertService.ts
import { DatabaseService } from './databaseService';
import { MetricsService } from './metricsService';
import { AlertDefinition, AlertInstance } from '../types/alerts';

export class AlertService {
  private dbService: DatabaseService;
  private metricsService: MetricsService;
  private activeAlerts: Map<string, AlertInstance> = new Map();

  constructor() {
    this.dbService = new DatabaseService();
    this.metricsService = new MetricsService();
    this.loadActiveAlerts();
  }

  async createAlert(alertDef: Omit<AlertDefinition, 'id'>): Promise<AlertDefinition> {
    const id = this.generateId();
    const alert = { ...alertDef, id };

    await this.dbService.insert('alert_rules', alert);
    return alert;
  }

  async updateAlert(id: string, updates: Partial<AlertDefinition>): Promise<void> {
    await this.dbService.update('alert_rules', { id, ...updates });
  }

  async deleteAlert(id: string): Promise<void> {
    await this.dbService.delete('alert_rules', { id });

    // Resolve any active instances
    if (this.activeAlerts.has(id)) {
      await this.resolveAlert(this.activeAlerts.get(id)!.id);
    }
  }

  async getAlerts(): Promise<AlertDefinition[]> {
    return await this.dbService.selectAll('alert_rules');
  }

  async getActiveAlerts(): Promise<AlertInstance[]> {
    return Array.from(this.activeAlerts.values());
  }

  async checkForNewAlerts(): Promise<AlertInstance[]> {
    const rules = await this.getAlerts();
    const enabledRules = rules.filter(rule => rule.enabled);
    const newAlerts: AlertInstance[] = [];

    for (const rule of enabledRules) {
      try {
        const metricValue = await this.metricsService.getLatestMetrics([rule.metric]);
        const currentValue = metricValue[rule.metric]?.value || 0;

        const isTriggered = this.evaluateCondition(currentValue, rule.threshold, rule.operator);
        const existingAlert = this.activeAlerts.get(rule.id);

        if (isTriggered && !existingAlert) {
          const alertInstance = await this.triggerAlert(rule, currentValue);
          newAlerts.push(alertInstance);
        } else if (!isTriggered && existingAlert) {
          await this.resolveAlert(existingAlert.id);
        }
      } catch (error) {
        console.error(`Error evaluating alert rule ${rule.id}:`, error);
      }
    }

    return newAlerts;
  }

  private async triggerAlert(rule: AlertDefinition, currentValue: number): Promise<AlertInstance> {
    const alert: AlertInstance = {
      id: this.generateId(),
      ruleId: rule.id,
      status: 'active',
      triggeredAt: Date.now(),
      currentValue,
      severity: rule.severity,
      message: `${rule.name}: ${rule.metric} is ${currentValue} (threshold: ${rule.threshold})`
    };

    this.activeAlerts.set(rule.id, alert);
    await this.dbService.insert('alert_instances', alert);

    // Send notifications
    await this.sendNotifications(alert, rule);

    return alert;
  }

  async resolveAlert(alertId: string): Promise<void> {
    let alertInstance: AlertInstance | undefined;

    // Find the alert instance
    for (const [ruleId, alert] of this.activeAlerts) {
      if (alert.id === alertId) {
        alertInstance = alert;
        break;
      }
    }

    if (alertInstance) {
      alertInstance.status = 'resolved';
      alertInstance.resolvedAt = Date.now();

      await this.dbService.update('alert_instances', {
        id: alertId,
        status: 'resolved',
        resolved_at: alertInstance.resolvedAt
      });

      this.activeAlerts.delete(alertInstance.ruleId);
    }
  }

  async acknowledgeAlert(alertId: string): Promise<void> {
    await this.dbService.update('alert_instances', {
      id: alertId,
      status: 'acknowledged',
      acknowledged_at: Date.now()
    });
  }

  private evaluateCondition(value: number, threshold: number, operator: string): boolean {
    switch (operator) {
      case 'gt':
        return value > threshold;
      case 'gte':
        return value >= threshold;
      case 'lt':
        return value < threshold;
      case 'lte':
        return value <= threshold;
      case 'eq':
        return value === threshold;
      default:
        return false;
    }
  }

  private async sendNotifications(alert: AlertInstance, rule: AlertDefinition): Promise<void> {
    for (const notification of rule.notifications) {
      try {
        switch (notification.type) {
          case 'email':
            await this.sendEmailNotification(alert, notification.target);
            break;
          case 'webhook':
            await this.sendWebhookNotification(alert, notification.target);
            break;
          case 'slack':
            await this.sendSlackNotification(alert, notification.target);
            break;
        }
      } catch (error) {
        console.error(`Failed to send ${notification.type} notification:`, error);
      }
    }
  }

  private async sendEmailNotification(alert: AlertInstance, email: string): Promise<void> {
    // Implementation depends on email service provider
    console.log(`Sending email notification to ${email}:`, alert.message);
  }

  private async sendWebhookNotification(alert: AlertInstance, webhookUrl: string): Promise<void> {
    await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ alert })
    });
  }

  private async sendSlackNotification(alert: AlertInstance, webhookUrl: string): Promise<void> {
    await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: alert.message,
        attachments: [{
          color: alert.severity === 'critical' ? 'danger' : 'warning',
          fields: [
            { title: 'Severity', value: alert.severity, short: true },
            { title: 'Current Value', value: alert.currentValue.toString(), short: true },
            { title: 'Triggered', value: new Date(alert.triggeredAt).toISOString(), short: true }
          ]
        }]
      })
    });
  }

  private async loadActiveAlerts(): Promise<void> {
    const activeAlerts = await this.dbService.query(
      'SELECT * FROM alert_instances WHERE status IN (?, ?)',
      ['active', 'acknowledged']
    );

    for (const alert of activeAlerts) {
      this.activeAlerts.set(alert.rule_id, {
        id: alert.id,
        ruleId: alert.rule_id,
        status: alert.status,
        triggeredAt: alert.triggered_at,
        resolvedAt: alert.resolved_at,
        acknowledgedAt: alert.acknowledged_at,
        currentValue: alert.current_value,
        severity: alert.severity,
        message: alert.message
      });
    }
  }

  private generateId(): string {
    return Math.random().toString(36).substr(2, 9);
  }
}
```

## 🧪 Testing Implementation

### 1. Frontend Component Testing

```typescript
// frontend/src/components/charts/__tests__/MetricChart.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MetricChart } from '../MetricChart';

describe('MetricChart', () => {
  const mockData = [
    { timestamp: Date.now() - 5000, value: 0.8 },
    { timestamp: Date.now() - 4000, value: 0.85 },
    { timestamp: Date.now() - 3000, value: 0.9 },
    { timestamp: Date.now() - 2000, value: 0.87 },
    { timestamp: Date.now() - 1000, value: 0.92 },
  ];

  it('renders chart with data', () => {
    render(
      <MetricChart
        data={mockData}
        metric="test_metric"
        title="Test Metric"
      />
    );

    expect(screen.getByText('Test Metric')).toBeInTheDocument();
  });

  it('handles empty data gracefully', () => {
    render(
      <MetricChart
        data={[]}
        metric="empty_metric"
      />
    );

    expect(screen.getByRole('img')).toBeInTheDocument();
  });

  it('applies custom color', () => {
    const { container } = render(
      <MetricChart
        data={mockData}
        metric="test_metric"
        color="#FF0000"
      />
    );

    const canvas = container.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
  });
});
```

### 2. Backend Service Testing

```typescript
// backend/src/services/__tests__/AlertService.test.ts
import { AlertService } from '../AlertService';
import { DatabaseService } from '../DatabaseService';
import { MetricsService } from '../MetricsService';

jest.mock('../DatabaseService');
jest.mock('../MetricsService');

describe('AlertService', () => {
  let alertService: AlertService;
  let mockDbService: jest.Mocked<DatabaseService>;
  let mockMetricsService: jest.Mocked<MetricsService>;

  beforeEach(() => {
    mockDbService = new DatabaseService() as jest.Mocked<DatabaseService>;
    mockMetricsService = new MetricsService() as jest.Mocked<MetricsService>;
    alertService = new AlertService();
  });

  describe('createAlert', () => {
    it('creates a new alert rule', async () => {
      const alertDef = {
        name: 'Test Alert',
        description: 'Test description',
        metric: 'test_metric',
        threshold: 0.8,
        operator: 'lt' as const,
        severity: 'warning' as const,
        enabled: true,
        cooldownPeriod: 300,
        notifications: []
      };

      mockDbService.insert.mockResolvedValue();

      const result = await alertService.createAlert(alertDef);

      expect(result).toMatchObject(alertDef);
      expect(result.id).toBeDefined();
      expect(mockDbService.insert).toHaveBeenCalledWith('alert_rules', expect.objectContaining(alertDef));
    });
  });

  describe('checkForNewAlerts', () => {
    it('triggers alert when threshold is crossed', async () => {
      const rule = {
        id: 'rule-1',
        name: 'Test Alert',
        metric: 'test_metric',
        threshold: 0.8,
        operator: 'lt' as const,
        severity: 'warning' as const,
        enabled: true,
        cooldownPeriod: 300,
        notifications: []
      };

      mockDbService.selectAll.mockResolvedValue([rule]);
      mockMetricsService.getLatestMetrics.mockResolvedValue({
        test_metric: { value: 0.7, timestamp: Date.now() }
      });
      mockDbService.insert.mockResolvedValue();

      const alerts = await alertService.checkForNewAlerts();

      expect(alerts).toHaveLength(1);
      expect(alerts[0].ruleId).toBe('rule-1');
      expect(alerts[0].currentValue).toBe(0.7);
      expect(alerts[0].status).toBe('active');
    });
  });
});
```

This implementation guide provides comprehensive technical specifications for building the DevStream Quality Monitoring Dashboard with TypeScript, React, and Node.js, following best practices for real-time data visualization and alert management systems.