"""
Webhook service for managing GitHub webhooks
"""
import os
from typing import Optional
from backend.models.project import Project

class WebhookService:
    def __init__(self):
        self.webhook_base_url = os.getenv("CLOUDFLARE_WORKER_URL", "https://webhook-gateway.pixeliumperfecto.workers.dev")
    
    async def setup_project_webhook(self, project: Project) -> bool:
        """Set up webhook for a project"""
        try:
            # TODO: Implement webhook setup logic
            # This would involve creating a webhook URL and registering it with GitHub
            webhook_url = f"{self.webhook_base_url}/webhook/{project.id}"
            project.webhook_url = webhook_url
            project.webhook_active = True
            
            print(f"Webhook setup for project {project.name}: {webhook_url}")
            return True
            
        except Exception as e:
            print(f"Error setting up webhook for project {project.name}: {e}")
            return False
