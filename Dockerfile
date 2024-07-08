FROM python:3.10.9-slim

# Update and install dependencies
RUN apt update && apt upgrade -y && \
    apt install git -y

# Set work directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt requirements.txt
RUN pip install -U pip && pip install -U -r requirements.txt

# Copy the rest of the application
COPY . .

# Set the entrypoint
CMD ["python", "bot.py"]
