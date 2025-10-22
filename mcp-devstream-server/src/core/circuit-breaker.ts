/**
 * Circuit Breaker for MCP Operations
 *
 * Prevents cascade failures by implementing circuit breaker pattern
 * with exponential backoff and graceful degradation
 */

export interface CircuitBreakerConfig {
    failureThreshold: number;
    recoveryTimeout: number;
    monitoringPeriod: number;
    expectedRecoveryTime: number;
}

export class CircuitBreaker {
    private config: CircuitBreakerConfig;
    private failureCount = 0;
    private lastFailureTime: number | null = null;
    private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';
    private monitorTimer: NodeJS.Timeout | null = null;

    constructor(config: CircuitBreakerConfig) {
        this.config = config;
        this.startMonitoring();
    }

    /**
     * Execute operation with circuit breaker protection
     */
    async execute<T>(operation: () => Promise<T>, operationName: string): Promise<T> {
        if (this.state === 'OPEN') {
            if (this.shouldAttemptReset()) {
                this.state = 'HALF_OPEN';
                console.error(`🔄 Circuit breaker HALF_OPEN for ${operationName}`);
            } else {
                throw new Error(`Circuit breaker OPEN for ${operationName}`);
            }
        }

        try {
            const result = await operation();
            this.onSuccess();
            return result;
        } catch (error) {
            this.onFailure(operationName, error);
            throw error;
        }
    }

    private onSuccess(): void {
        this.failureCount = 0;
        this.lastFailureTime = null;

        if (this.state === 'HALF_OPEN') {
            this.state = 'CLOSED';
            console.error('✅ Circuit breaker CLOSED - operations resumed');
        }
    }

    private onFailure(operationName: string, error: any): void {
        this.failureCount++;
        this.lastFailureTime = Date.now();

        console.error(`❌ Circuit breaker failure ${this.failureCount}/${this.config.failureThreshold} for ${operationName}: ${error}`);

        if (this.failureCount >= this.config.failureThreshold) {
            this.state = 'OPEN';
            console.error(`🚨 Circuit breaker OPENED for ${operationName} - backing off for ${this.config.recoveryTimeout}ms`);

            // Schedule recovery attempt
            setTimeout(() => {
                this.state = 'HALF_OPEN';
                console.error(`🔄 Circuit breaker HALF_OPEN for ${operationName} - testing recovery`);
            }, this.config.recoveryTimeout);
        }
    }

    private shouldAttemptReset(): boolean {
        if (!this.lastFailureTime) return false;
        return Date.now() - this.lastFailureTime > this.config.expectedRecoveryTime;
    }

    private startMonitoring(): void {
        this.monitorTimer = setInterval(() => {
            if (this.failureCount > 0 && Date.now() - (this.lastFailureTime || 0) > this.config.monitoringPeriod) {
                console.error(`📊 Circuit breaker stats: ${this.failureCount} failures in monitoring period`);
                this.failureCount = Math.max(0, this.failureCount - 1);
            }
        }, this.config.monitoringPeriod);
    }

    destroy(): void {
        if (this.monitorTimer) {
            clearInterval(this.monitorTimer);
            this.monitorTimer = null;
        }
    }

    getState(): string {
        return this.state;
    }

    getStats(): { state: string; failures: number; lastFailure: number | null } {
        return {
            state: this.state,
            failures: this.failureCount,
            lastFailure: this.lastFailureTime
        };
    }
}