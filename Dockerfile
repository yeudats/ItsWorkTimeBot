# נשתמש בגרסה המדויקת שאתה צריך
FROM python:3.12.10

# נגדיר משתנים שמונעים בעיות timezone
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# נגדיר תיקיית עבודה
WORKDIR /app

# נעתיק את הקבצים
COPY requirements.txt /app/
COPY . /app/

# נתקין את התלויות
RUN pip install --no-cache-dir -r requirements.txt

# נפתח פורט
EXPOSE 10000

# פקודת הרצה
CMD ["python", "app.py"]
