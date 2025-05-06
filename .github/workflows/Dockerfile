# Minimal Dockerfile for Flask app
FROM python:3.9-slim #استخدم نسخة خفيفة من بايثون 3.9 كنقطة بداية

WORKDIR /app #حدد المجلد الرئيسي للتطبيق
COPY . /app #نسخ الملفات إلى المجلد الرئيسي

RUN pip install --no-cache-dir flask #تثبيت flask

CMD ["python", "app.py"] #الامر الذي يشغله الcontainer عند تشغيله
