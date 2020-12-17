FROM ubuntu:20.04

RUN apt-get update -y && apt-get install -y libasound2 python3-pip

COPY start.sh requirements.txt app.py cloudlanguagetools ./
RUN pip3 install -r requirements.txt

ENV PYTHONPATH "${PYTHONPATH}:."

EXPOSE 8042
ENTRYPOINT ["./start.sh"]