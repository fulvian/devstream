/**
 * DevStream Error Tracking
 *
 * Context7-compliant error tracking and alerting for production monitoring.
 * Simple but effective error categorization and metrics.
 */

import * as promClient from 'prom-client';
import { metricsRegistry } from './metrics.js';

/**
 * Error Counter by Category
 * Context7 pattern: Categorize errors for better debugging
 */
export const errorCounter = new promClient.Counter({
  name: 'devstream_errors_total',
  help: 'Total number of errors by category and severity',
  labelNames: ['category', 'severity', 'operation'],
  registers: [metricsRegistry],
});

/**
 * Error Categories
 */
export enum ErrorCategory {
  DATABASE = 'database',
  EMBEDDING = 'embedding',
  VECTOR_SEARCH = 'vector_search',
  FTS_SEARCH = 'fts_search',
  VALIDATION = 'validation',
  NETWORK = 'network',
  UNKNOWN = 'unknown',
}

/**
 * Error Severity Levels
 */
export enum ErrorSeverity {
  LOW = 'low',          // Recoverable, doesn't impact functionality
  MEDIUM = 'medium',    // Impacts performance but recoverable
  HIGH = 'high',        // Impacts functionality, needs attention
  CRITICAL = 'critical', // System failure, immediate action required
}

/**
 * Error Tracker
 * Context7 pattern: Centralized error tracking with metrics
 */
export class ErrorTracker {
  /**
   * Track an error with automatic categorization
   */
  static trackError(
    error: Error,
    category: ErrorCategory,
    severity: ErrorSeverity,
    operation: string
  ): void {
    // Increment error counter
    errorCounter.inc({
      category,
      severity,
      operation,
    });

    // Log error with context
    const timestamp = new Date().toISOString();
    console.error(`[${timestamp}] [${severity.toUpperCase()}] ${category}/${operation}:`, error.message);

    // For critical errors, log stack trace
    if (severity === ErrorSeverity.CRITICAL && error.stack) {
      console.error('Stack trace:', error.stack);
    }
  }

  /**
   * Track database errors
   */
  static trackDatabaseError(error: Error, operation: string): void {
    const severity = error.message.includes('SQLITE_BUSY')
      ? ErrorSeverity.MEDIUM
      : ErrorSeverity.HIGH;

    this.trackError(error, ErrorCategory.DATABASE, severity, operation);
  }

  /**
   * Track embedding generation errors
   */
  static trackEmbeddingError(error: Error, operation: string): void {
    // Embedding failures are usually recoverable (fallback to keyword search)
    this.trackError(error, ErrorCategory.EMBEDDING, ErrorSeverity.MEDIUM, operation);
  }

  /**
   * Track vector search errors
   */
  static trackVectorSearchError(error: Error, operation: string): void {
    this.trackError(error, ErrorCategory.VECTOR_SEARCH, ErrorSeverity.MEDIUM, operation);
  }

  /**
   * Track FTS5 search errors
   */
  static trackFTSSearchError(error: Error, operation: string): void {
    // FTS5 errors are more serious as it's our fallback
    this.trackError(error, ErrorCategory.FTS_SEARCH, ErrorSeverity.HIGH, operation);
  }

  /**
   * Track validation errors
   */
  static trackValidationError(error: Error, operation: string): void {
    // Validation errors are low severity (user input issues)
    this.trackError(error, ErrorCategory.VALIDATION, ErrorSeverity.LOW, operation);
  }

  /**
   * Get error statistics
   */
  static async getErrorStats() {
    return {
      error_tracking: {
        description: 'Total errors by category and severity',
        metric: 'devstream_errors_total',
      },
      categories: Object.values(ErrorCategory),
      severities: Object.values(ErrorSeverity),
    };
  }
}

/**
 * Error Alert Thresholds
 * Context7 pattern: Define when to alert
 */
export const ERROR_THRESHOLDS = {
  critical_per_minute: 1,    // Alert if ≥1 critical error per minute
  high_per_minute: 5,        // Alert if ≥5 high severity errors per minute
  medium_per_minute: 20,     // Alert if ≥20 medium severity errors per minute
  total_per_minute: 50,      // Alert if ≥50 total errors per minute
};

/**
 * Simple in-memory error rate tracker
 * For production, use external alerting (Prometheus Alertmanager)
 */
class ErrorRateTracker {
  private recentErrors: Map<string, number[]> = new Map();
  private readonly windowMs = 60000; // 1 minute window

  track(key: string): void {
    const now = Date.now();

    if (!this.recentErrors.has(key)) {
      this.recentErrors.set(key, []);
    }

    const errors = this.recentErrors.get(key)!;
    errors.push(now);

    // Clean old errors outside window
    const cutoff = now - this.windowMs;
    this.recentErrors.set(
      key,
      errors.filter(timestamp => timestamp > cutoff)
    );
  }

  getRate(key: string): number {
    return this.recentErrors.get(key)?.length || 0;
  }

  checkThresholds(): string[] {
    const alerts: string[] = [];

    // Check critical errors
    const criticalRate = this.getRate('critical');
    if (criticalRate >= ERROR_THRESHOLDS.critical_per_minute) {
      alerts.push(`⚠️  ALERT: ${criticalRate} critical errors in last minute (threshold: ${ERROR_THRESHOLDS.critical_per_minute})`);
    }

    // Check high severity
    const highRate = this.getRate('high');
    if (highRate >= ERROR_THRESHOLDS.high_per_minute) {
      alerts.push(`⚠️  WARNING: ${highRate} high-severity errors in last minute (threshold: ${ERROR_THRESHOLDS.high_per_minute})`);
    }

    return alerts;
  }
}

export const globalErrorTracker = new ErrorRateTracker();