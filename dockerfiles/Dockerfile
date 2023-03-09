FROM python:3.9.5

RUN apt update && apt install cron -y
RUN pip install -U pip

COPY ./init.sh /
COPY ./cron_settings /etc/cron.d/

RUN chmod 744 /init.sh
RUN chmod 644 /etc/cron.d/cron_settings

WORKDIR /sleepbattle

CMD ["/init.sh"]
