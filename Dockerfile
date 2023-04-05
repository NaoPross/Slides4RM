FROM alpine

RUN apk update --no-cache \
	&& apk upgrade \
	&& apk add python3 \
	&& apk add wget perl xz tar fontconfig freetype lua gcc

RUN adduser -S u

USER u
WORKDIR /home/u
ENV PATH=/home/u/.TinyTeX/bin/x86_64-linuxmusl/:/home/u/.local/bin:$PATH

RUN wget -qO- "https://yihui.org/tinytex/install-unx.sh" | sh
RUN tlmgr install xetex titling roboto fancyhdr pgf geometry graphics

ENV PYTHONUNBUFFERED=1
RUN python3 -m ensurepip && python3 -m pip install pyuwsgi colorlog werkzeug flask pdfminer

COPY . /home/u

ENTRYPOINT ["uwsgi", "--http", ":8000", "--enable-threads", "--harakiri", "180", "--master", "-p", "4", "-w", "slides4rm:app"]
EXPOSE 8000
