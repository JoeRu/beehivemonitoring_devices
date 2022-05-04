FROM python:3.8

RUN apt-get update && apt-get install -y \
    python3-pip 
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip3 install paho-mqtt


RUN mkdir /opt/bluezQt
RUN mkdir /export
COPY bluezQt.py /opt/bluezQt/
CMD ["python", "/opt/bluezQt/bluezQt.py"]
