FROM python:3-alpine
ENV PYTHONUNBUFFERED 1

RUN apk add --no-cache musl-dev gcc make libffi-dev postgresql-dev ffmpeg

RUN adduser -Ds /bin/nologin boltstream
USER boltstream
RUN mkdir -p /home/boltstream/app/
WORKDIR
ENV PATH="/home/boltstream/.local/bin:${PATH}"

COPY --chown=boltstream:boltstream requirements.txt requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

COPY --chown=boltstream:boltstream manage.py /home/boltstream/app/
COPY --chown=boltstream:boltstream ./boltstream /home/boltstream/app/boltstream

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.wsgi:application"]
