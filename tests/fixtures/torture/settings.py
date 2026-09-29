"""DRF settings — resolvable auth default + external host constants (mirrors real example settings)."""
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
}
PAYMENT_URL = "https://pay.example.com/charge"
CRM_URL = "https://api.crm.example.com/v2/lead.capture"
CRM_WEBHOOK_URL = "https://crm.example.com/hook"
S3_BUCKET = "example-media"
