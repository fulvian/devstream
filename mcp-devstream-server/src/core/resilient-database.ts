/**
 * Resilient Database Wrapper with Circuit Breaker
 *
 * Wraps database operations with circuit breaker protection
 * and enhanced error handling
 */

import { DevStreamDatabase } from '../database.js';
import { CircuitBreaker } from './circuit-breaker.js';

export class ResilientDatabase {
    private database: DevStreamDatabase;
    private circuitBreaker: CircuitBreaker;
    private retryAttempts: number = 3;

    constructor(database: DevStreamDatabase) {
        this.database = database;
        this.circuitBreaker = new CircuitBreaker({
            failureThreshold: 5,
            recoveryTimeout: 30000, // 30 seconds
            monitoringPeriod: 60000, // 1 minute
            expectedRecoveryTime: 10000 // 10 seconds
        });
    }

    async query<T = any>(sql: string, params: any[] = []): Promise<T[]> {
        return await this.circuitBreaker.execute(
            () => this.database.query<T>(sql, params),
            `database.query: ${sql.substring(0, 50)}...`
        );
    }

    async queryOne<T = any>(sql: string, params: any[] = []): Promise<T | null> {
        return await this.circuitBreaker.execute(
            () => this.database.queryOne<T>(sql, params),
            `database.queryOne: ${sql.substring(0, 50)}...`
        );
    }

    async execute(sql: string, params: any[] = []): Promise<{ lastID?: number; changes: number }> {
        return await this.circuitBreaker.execute(
            () => this.database.execute(sql, params),
            `database.execute: ${sql.substring(0, 50)}...`
        );
    }

    async initialize(): Promise<void> {
        await this.circuitBreaker.execute(
            () => this.database.initialize(),
            'database.initialize'
        );
    }

    async close(): Promise<void> {
        this.circuitBreaker.destroy();
        await this.database.close();
    }

    getStats(): any {
        return {
            circuitBreaker: this.circuitBreaker.getStats(),
            database: this.database.isConnected()
        };
    }
}