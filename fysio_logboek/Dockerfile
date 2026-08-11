FROM python:3.12-alpine

RUN pip install --no-cache-dir "fastapi==0.115.*" "uvicorn[standard]==0.32.*"

WORKDIR /app
COPY app/ /app/
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
