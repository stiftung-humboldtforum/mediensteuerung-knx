FROM python:3.12-slim

RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir --upgrade \
	asyncclick==8.3.0.7 \
	requests==2.34.2 \
	aiomqtt==2.5.1 \
	paho-mqtt==2.1.0 \
	xknx==3.16.0
