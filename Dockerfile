FROM python:3.11-slim

RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir --upgrade \
	asyncclick==8.3.0.7 \
	anyio==3.6.2 \
	requests==2.34.2 \
	aiomqtt==1.1.0 \
	xknx==2.11.2
