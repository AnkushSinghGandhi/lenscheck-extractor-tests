"""DRF settings — a SECURE default (IsAuthenticated), a JWT authenticator, and external host consts.
Endpoints with no permission_classes inherit IsAuthenticated; apps override per-endpoint to exercise
the full auth matrix (AllowAny / IsAdminUser / a permission constant / a custom class / open []).
"""
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
}
PAYMENT_URL = "https://pay.example.com/charge"
RAZORPAY_URL = "https://api.razorpay.com/v1/payments"
CRM_URL = "https://api.crm.example.com/v2/lead.capture"
ANALYTICS_URL = "https://analytics.example.com/track"
S3_BUCKET = "megashop-media"
