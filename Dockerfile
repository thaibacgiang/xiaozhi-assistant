FROM python:3.12-slim
WORKDIR /app
COPY ./app /app
COPY run.sh /run.sh
RUN chmod +x /run.sh
RUN pip3 install --no-cache-dir -r requirements.txt
CMD [ "/run.sh" ]
