# Dockerfile
FROM python:3.10

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /telegram-bot

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code
COPY bot ./bot
COPY main.py .
COPY .env .
COPY feedback_log.db
COPY questions_log.db
COPY admin_bot.py .
# Command to run the bot
CMD python main.py & python admin_bot.py & wait
