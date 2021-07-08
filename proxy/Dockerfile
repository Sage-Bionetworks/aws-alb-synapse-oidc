FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
    apache2 \
    ssl-cert \
    libapache2-mod-python \
    zlib1g-dev \
    libclang-dev \
    libssl-dev \
    libffi-dev \
    libcurl4-openssl-dev \
    libapparmor1 \
    libssl1.0.0 \
    libxml2-dev \
    python-cryptography \
    python-jwt \
    python-requests

COPY access.py /usr/lib/cgi-bin/access.py
RUN chmod 0755 /usr/lib/cgi-bin/access.py

COPY proxy.conf /etc/apache2/sites-available/proxy.conf

ARG TARGET_HOST
RUN sed -i "s/TARGET_HOST/${TARGET_HOST}/g" /etc/apache2/sites-available/proxy.conf

RUN a2enmod ssl proxy proxy_http rewrite python headers

RUN a2ensite proxy

RUN a2dissite 000-default

EXPOSE 443

CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"] 
