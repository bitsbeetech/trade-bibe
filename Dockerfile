FROM    python:3.6.2

RUN pip install numpy
RUN apt-get update
RUN apt-get -y install build-essential  
RUN  wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
RUN tar zxvf ta-lib-0.4.0-src.tar.gz
RUN cd ta-lib && ./configure && make && make install
ENV LD_LIBRARY_PATH /usr/local/lib

RUN apt-get install -y sqlite3 libsqlite3-dev
RUN mkdir /db
RUN /usr/bin/sqlite3 /db/tradesv2.dry_run.sqlite
RUN /usr/bin/sqlite3 /db/tradesv2.sqlite

RUN     mkdir -p /tradebibe
WORKDIR /tradebibe

ADD     ./requirements.txt /tradebibe/requirements.txt
RUN     pip install -r requirements.txt
ADD     . /tradebibe
CMD     /bin/bash
