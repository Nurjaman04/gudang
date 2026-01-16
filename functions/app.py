from app import create_app
import aws_wsgi

# Membuat aplikasi Flask
app = create_app()

# Handler untuk Netlify Functions (AWS Lambda)
def handler(event, context):
    return aws_wsgi.response(app, event, context)
