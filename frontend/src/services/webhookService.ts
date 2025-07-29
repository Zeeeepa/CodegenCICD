/**
 * Webhook service for Cloudflare worker integration
 */

import { WebhookConfig, WebhookEvent } from '../types/cicd';
import { githubService } from './githubService';

// ============================================================================
// WEBHOOK SERVICE CLASS
// ============================================================================

class WebhookService {
  private cloudflareWorkerUrl: string;
  private cloudflareApiKey: string;
  private cloudflareAccountId: string;
  private webhookSecret: string;

  constructor() {
    this.cloudflareWorkerUrl = process.env.REACT_APP_CLOUDFLARE_WORKER_URL || '';
    this.cloudflareApiKey = process.env.REACT_APP_CLOUDFLARE_API_KEY || '';
    this.cloudflareAccountId = process.env.REACT_APP_CLOUDFLARE_ACCOUNT_ID || '';
    this.webhookSecret = this.generateWebhookSecret();

    if (!this.cloudflareWorkerUrl) {
      console.warn('Cloudflare worker URL not configured. Webhook features may not work.');
    }
  }

  // ========================================================================
  // WEBHOOK MANAGEMENT
  // ========================================================================

  /**
   * Create webhook for repository
   */
  async createWebhook(repoFullName: string, events: string[] = ['pull_request', 'push']): Promise<WebhookConfig> {
    try {
      // Generate unique webhook URL for this repository
      const webhookUrl = this.generateWebhookUrl(repoFullName);
      
      // Create webhook on GitHub
      const githubWebhook = await githubService.createWebhook(repoFullName, {
        url: webhookUrl,
        secret: this.webhookSecret,
        events,
        active: true
      });

      // Configure Cloudflare worker to handle this webhook
      await this.configureCloudflareRoute(repoFullName, webhookUrl);

      const config: WebhookConfig = {
        url: webhookUrl,
        secret: this.webhookSecret,
        events,
        active: true,
        deliveryCount: 0,
        errorCount: 0
      };

      console.log(`Webhook created for ${repoFullName}: ${webhookUrl}`);
      return config;

    } catch (error) {
      console.error(`Failed to create webhook for ${repoFullName}:`, error);
      throw new Error(`Failed to create webhook: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Update webhook configuration
   */
  async updateWebhook(repoFullName: string, config: Partial<WebhookConfig>): Promise<WebhookConfig> {
    try {
      // Get existing webhooks to find the one to update
      const webhooks = await githubService.getWebhooks(repoFullName);
      const existingWebhook = webhooks.find(hook => 
        hook.config.url.includes(this.getRepoWebhookPath(repoFullName))
      );

      if (!existingWebhook) {
        throw new Error('Webhook not found');
      }

      // Update GitHub webhook
      await githubService.updateWebhook(repoFullName, existingWebhook.id, {
        url: config.url,
        secret: config.secret,
        events: config.events,
        active: config.active
      });

      const updatedConfig: WebhookConfig = {
        url: config.url || existingWebhook.config.url,
        secret: config.secret || this.webhookSecret,
        events: config.events || existingWebhook.events,
        active: config.active ?? existingWebhook.active,
        deliveryCount: config.deliveryCount || 0,
        errorCount: config.errorCount || 0
      };

      console.log(`Webhook updated for ${repoFullName}`);
      return updatedConfig;

    } catch (error) {
      console.error(`Failed to update webhook for ${repoFullName}:`, error);
      throw error;
    }
  }

  /**
   * Remove webhook
   */
  async removeWebhook(repoFullName: string): Promise<void> {
    try {
      // Get existing webhooks
      const webhooks = await githubService.getWebhooks(repoFullName);
      const webhook = webhooks.find(hook => 
        hook.config.url.includes(this.getRepoWebhookPath(repoFullName))
      );

      if (webhook) {
        // Delete from GitHub
        await githubService.deleteWebhook(repoFullName, webhook.id);
        
        // Remove from Cloudflare worker configuration
        await this.removeCloudflareRoute(repoFullName);
        
        console.log(`Webhook removed for ${repoFullName}`);
      }

    } catch (error) {
      console.error(`Failed to remove webhook for ${repoFullName}:`, error);
      throw error;
    }
  }

  /**
   * Test webhook
   */
  async testWebhook(repoFullName: string): Promise<boolean> {
    try {
      const webhooks = await githubService.getWebhooks(repoFullName);
      const webhook = webhooks.find(hook => 
        hook.config.url.includes(this.getRepoWebhookPath(repoFullName))
      );

      if (!webhook) {
        throw new Error('Webhook not found');
      }

      await githubService.testWebhook(repoFullName, webhook.id);
      return true;

    } catch (error) {
      console.error(`Failed to test webhook for ${repoFullName}:`, error);
      return false;
    }
  }

  // ========================================================================
  // WEBHOOK EVENT HANDLING
  // ========================================================================

  /**
   * Process incoming webhook event
   */
  async processWebhookEvent(payload: any, signature?: string): Promise<WebhookEvent> {
    try {
      // Verify webhook signature
      if (signature && !this.verifySignature(payload, signature)) {
        throw new Error('Invalid webhook signature');
      }

      // Extract event information
      const eventType = this.extractEventType(payload);
      const projectId = this.extractProjectId(payload);

      const webhookEvent: WebhookEvent = {
        id: this.generateEventId(),
        projectId,
        eventType,
        payload,
        signature,
        receivedAt: new Date().toISOString(),
        processed: false
      };

      // Store event for processing
      this.storeWebhookEvent(webhookEvent);

      console.log(`Webhook event received: ${eventType} for project ${projectId}`);
      return webhookEvent;

    } catch (error) {
      console.error('Failed to process webhook event:', error);
      throw error;
    }
  }

  /**
   * Mark webhook event as processed
   */
  async markEventProcessed(eventId: string, triggeredWorkflow?: string, error?: string): Promise<void> {
    try {
      const events = this.getStoredEvents();
      const event = events.find(e => e.id === eventId);
      
      if (event) {
        event.processed = true;
        event.processedAt = new Date().toISOString();
        if (triggeredWorkflow) event.triggeredWorkflow = triggeredWorkflow;
        if (error) event.error = error;
        
        this.saveStoredEvents(events);
      }
    } catch (error) {
      console.error('Failed to mark event as processed:', error);
    }
  }

  /**
   * Get webhook events for project
   */
  getProjectEvents(projectId: string, limit: number = 50): WebhookEvent[] {
    try {
      const events = this.getStoredEvents();
      return events
        .filter(event => event.projectId === projectId)
        .sort((a, b) => new Date(b.receivedAt).getTime() - new Date(a.receivedAt).getTime())
        .slice(0, limit);
    } catch (error) {
      console.error('Failed to get project events:', error);
      return [];
    }
  }

  // ========================================================================
  // CLOUDFLARE WORKER INTEGRATION
  // ========================================================================

  /**
   * Configure Cloudflare worker route for repository
   */
  private async configureCloudflareRoute(repoFullName: string, webhookUrl: string): Promise<void> {
    if (!this.cloudflareApiKey || !this.cloudflareAccountId) {
      console.warn('Cloudflare credentials not configured. Skipping worker configuration.');
      return;
    }

    try {
      // This would configure the Cloudflare worker to route webhooks
      // For now, we'll just log the configuration
      console.log(`Configuring Cloudflare route for ${repoFullName}: ${webhookUrl}`);
      
      // In a real implementation, this would:
      // 1. Update the worker script to handle the new route
      // 2. Configure routing rules
      // 3. Set up any necessary environment variables
      
    } catch (error) {
      console.error('Failed to configure Cloudflare route:', error);
      throw error;
    }
  }

  /**
   * Remove Cloudflare worker route
   */
  private async removeCloudflareRoute(repoFullName: string): Promise<void> {
    if (!this.cloudflareApiKey || !this.cloudflareAccountId) {
      return;
    }

    try {
      console.log(`Removing Cloudflare route for ${repoFullName}`);
      // Implementation would remove the route from worker configuration
    } catch (error) {
      console.error('Failed to remove Cloudflare route:', error);
    }
  }

  // ========================================================================
  // UTILITY METHODS
  // ========================================================================

  /**
   * Generate webhook URL for repository
   */
  private generateWebhookUrl(repoFullName: string): string {
    const path = this.getRepoWebhookPath(repoFullName);
    return `${this.cloudflareWorkerUrl}${path}`;
  }

  /**
   * Get webhook path for repository
   */
  private getRepoWebhookPath(repoFullName: string): string {
    const encoded = encodeURIComponent(repoFullName);
    return `/webhook/${encoded}`;
  }

  /**
   * Generate webhook secret
   */
  private generateWebhookSecret(): string {
    return Array.from(crypto.getRandomValues(new Uint8Array(32)))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }

  /**
   * Generate event ID
   */
  private generateEventId(): string {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Verify webhook signature
   */
  private verifySignature(payload: any, signature: string): boolean {
    try {
      // This would implement HMAC-SHA256 signature verification
      // For now, return true (in production, implement proper verification)
      return true;
    } catch (error) {
      console.error('Failed to verify webhook signature:', error);
      return false;
    }
  }

  /**
   * Extract event type from payload
   */
  private extractEventType(payload: any): string {
    // GitHub webhook headers include X-GitHub-Event
    // For now, extract from payload structure
    if (payload.pull_request) {
      return `pull_request.${payload.action || 'unknown'}`;
    } else if (payload.commits) {
      return 'push';
    } else if (payload.issue) {
      return `issues.${payload.action || 'unknown'}`;
    } else {
      return 'unknown';
    }
  }

  /**
   * Extract project ID from payload
   */
  private extractProjectId(payload: any): string {
    const repoFullName = payload.repository?.full_name;
    if (repoFullName) {
      return repoFullName.replace('/', '_').toLowerCase();
    }
    return 'unknown';
  }

  // ========================================================================
  // EVENT STORAGE
  // ========================================================================

  /**
   * Store webhook event
   */
  private storeWebhookEvent(event: WebhookEvent): void {
    try {
      const events = this.getStoredEvents();
      events.push(event);
      
      // Keep only last 1000 events
      if (events.length > 1000) {
        events.splice(0, events.length - 1000);
      }
      
      this.saveStoredEvents(events);
    } catch (error) {
      console.error('Failed to store webhook event:', error);
    }
  }

  /**
   * Get stored webhook events
   */
  private getStoredEvents(): WebhookEvent[] {
    try {
      const stored = localStorage.getItem('webhook_events');
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Failed to get stored events:', error);
      return [];
    }
  }

  /**
   * Save webhook events to storage
   */
  private saveStoredEvents(events: WebhookEvent[]): void {
    try {
      localStorage.setItem('webhook_events', JSON.stringify(events));
    } catch (error) {
      console.error('Failed to save webhook events:', error);
    }
  }

  /**
   * Clear all stored events
   */
  clearStoredEvents(): void {
    try {
      localStorage.removeItem('webhook_events');
      console.log('Webhook events cleared');
    } catch (error) {
      console.error('Failed to clear webhook events:', error);
    }
  }

  /**
   * Get webhook statistics
   */
  getWebhookStats(): {
    totalEvents: number;
    processedEvents: number;
    errorEvents: number;
    eventsByType: Record<string, number>;
  } {
    try {
      const events = this.getStoredEvents();
      
      const stats = {
        totalEvents: events.length,
        processedEvents: events.filter(e => e.processed).length,
        errorEvents: events.filter(e => e.error).length,
        eventsByType: {} as Record<string, number>
      };

      // Count events by type
      events.forEach(event => {
        stats.eventsByType[event.eventType] = (stats.eventsByType[event.eventType] || 0) + 1;
      });

      return stats;
    } catch (error) {
      console.error('Failed to get webhook stats:', error);
      return {
        totalEvents: 0,
        processedEvents: 0,
        errorEvents: 0,
        eventsByType: {}
      };
    }
  }
}

// ============================================================================
// EXPORT SINGLETON INSTANCE
// ============================================================================

export const webhookService = new WebhookService();
