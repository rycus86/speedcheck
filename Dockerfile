ARG BASE_IMAGE=alpine

FROM ${BASE_IMAGE}

RUN apk add --no-cache python3

ADD requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt

ADD server.py /var/app/server
ADD client.py /var/app/client

WORKDIR /var/app

STOPSIGNAL SIGINT

ENTRYPOINT [ "/usr/bin/python3", "-u" ]
CMD [ "server" ]
