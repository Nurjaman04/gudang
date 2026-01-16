from app import create_app
import serverless_http

# Membuat aplikasi Flask
app = create_app()

# Handler untuk Netlify Functions (AWS Lambda)
handler = serverless_http.handler(app)
