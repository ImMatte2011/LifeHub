FROM postgis/postgis:16-3.4-alpine
COPY backup-loop.sh /usr/local/bin/lifehub-backup-loop
RUN sed -i 's/\r$//' /usr/local/bin/lifehub-backup-loop
ENTRYPOINT ["/bin/sh", "/usr/local/bin/lifehub-backup-loop"]
