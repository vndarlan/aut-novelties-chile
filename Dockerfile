# Dockerfile otimizado para Dropi Chile Background Bot
FROM python:3.11-slim

# Instala dependências do sistema necessárias para Chrome e Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Adiciona repositório do Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list

# Instala Google Chrome
RUN apt-get update && apt-get install -y \
    google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Instala ChromeDriver
RUN CHROME_DRIVER_VERSION=`curl -sS https://chromedriver.chromium.org/downloads | grep -Po "(?<=ChromeDriver )[0-9.]+" | head -1` \
    && wget -N https://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip -P ~/ \
    && unzip ~/chromedriver_linux64.zip -d ~/ \
    && rm ~/chromedriver_linux64.zip \
    && mv ~/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos de requirements
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

# Cria diretório para screenshots
RUN mkdir -p screenshots

# Define variáveis de ambiente para Chrome
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_DRIVER=/usr/local/bin/chromedriver
ENV DISPLAY=:99

# Cria usuário não-root para segurança
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Comando para iniciar o bot em background
CMD ["python", "chile_background_bot.py"]