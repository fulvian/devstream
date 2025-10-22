/**
 * Session Manager for MCP Server
 *
 * Provides session ID generation and tracking for PostToolUse hook compatibility
 * Maintains session state and cleanup
 */

import { randomUUID } from 'crypto';
import { DevStreamDatabase } from '../database.js';

export class SessionManager {
    private database: DevStreamDatabase;
    private currentSessionId: string | null = null;
    private sessionStartTime: Date | null = null;

    constructor(database: DevStreamDatabase) {
        this.database = database;
    }

    /**
     * Initialize or get current session
     */
    async getCurrentOrCreateSession(): Promise<string> {
        // Try to get existing session from database
        const existingSession = await this.database.queryOne<{ id: string }>(`
            SELECT id FROM work_sessions
            WHERE status = 'active'
            ORDER BY last_activity_at DESC
            LIMIT 1
        `);

        if (existingSession) {
            // Update activity and return existing session
            await this.database.execute(`
                UPDATE work_sessions
                SET last_activity_at = CURRENT_TIMESTAMP
                WHERE id = ?
            `, [existingSession.id]);

            this.currentSessionId = existingSession.id;
            console.error(`📋 Using existing session: ${existingSession.id}`);
            return existingSession.id;
        }

        // Create new session
        return await this.createNewSession();
    }

    private async createNewSession(): Promise<string> {
        const sessionId = `sess-${randomUUID().substring(0, 8)}`;

        await this.database.execute(`
            INSERT INTO work_sessions (id, user_id, session_name, status, started_at, last_activity_at)
            VALUES (?, ?, ?, ?, ?, ?)
        `, [
            sessionId,
            'claude-code',
            `MCP Session ${new Date().toISOString()}`,
            'active',
            new Date().toISOString(),
            new Date().toISOString()
        ]);

        this.currentSessionId = sessionId;
        this.sessionStartTime = new Date();

        console.error(`🆕 Created new MCP session: ${sessionId}`);
        return sessionId;
    }

    /**
     * Get session statistics
     */
    async getSessionStats(): Promise<{
        sessionId: string | null;
        uptime: number | null;
        isActive: boolean;
    }> {
        if (!this.currentSessionId) {
            return { sessionId: null, uptime: null, isActive: false };
        }

        const session = await this.database.queryOne<{ last_activity_at: string }>(`
            SELECT last_activity_at FROM work_sessions WHERE id = ? AND status = 'active'
        `, [this.currentSessionId]);

        return {
            sessionId: this.currentSessionId,
            uptime: this.sessionStartTime ? Date.now() - this.sessionStartTime.getTime() : null,
            isActive: !!session
        };
    }

    /**
     * End current session
     */
    async endCurrentSession(): Promise<void> {
        if (!this.currentSessionId) return;

        await this.database.execute(`
            UPDATE work_sessions
            SET status = 'completed', ended_at = ?
            WHERE id = ?
        `, [new Date().toISOString(), this.currentSessionId]);

        console.error(`🏁 Session ended: ${this.currentSessionId}`);
        this.currentSessionId = null;
        this.sessionStartTime = null;
    }
}

// Singleton instance
let sessionManagerInstance: SessionManager | null = null;

export function getSessionManager(database: DevStreamDatabase): SessionManager {
    if (!sessionManagerInstance) {
        sessionManagerInstance = new SessionManager(database);
    }
    return sessionManagerInstance;
}